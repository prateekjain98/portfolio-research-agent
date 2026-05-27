"use client";

import type { UseChatHelpers } from "@ai-sdk/react";
import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { usePathname } from "next/navigation";
import {
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import useSWR, { useSWRConfig } from "swr";
import { unstable_serialize } from "swr/infinite";
import { useDataStream } from "@/components/chat/data-stream-provider";
import { getChatHistoryPaginationKey } from "@/components/chat/sidebar-history";
import { toast } from "@/components/chat/toast";
import type { VisibilityType } from "@/components/chat/visibility-selector";
import { useAutoResume } from "@/hooks/use-auto-resume";
import { DEFAULT_CHAT_MODEL } from "@/lib/ai/models";
import type { Vote } from "@/lib/db/schema";
import { ChatbotError } from "@/lib/errors";
import type { ChatMessage } from "@/lib/types";
import { fetcher, fetchWithErrorHandlers, generateUUID, getTextFromMessage } from "@/lib/utils";
import { ensureUser, createChat, createMessages, generateTitleFromUserMessage } from "@/app/(chat)/actions";

function setCookie(name: string, value: string) {
  const maxAge = 60 * 60 * 24 * 365;
  // biome-ignore lint/suspicious/noDocumentCookie: needed for client-side cookie setting
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}`;
}

type ActiveChatContextValue = {
  chatId: string;
  messages: ChatMessage[];
  setMessages: UseChatHelpers<ChatMessage>["setMessages"];
  sendMessage: UseChatHelpers<ChatMessage>["sendMessage"];
  status: UseChatHelpers<ChatMessage>["status"];
  error: UseChatHelpers<ChatMessage>["error"];
  stop: UseChatHelpers<ChatMessage>["stop"];
  regenerate: UseChatHelpers<ChatMessage>["regenerate"];
  addToolApprovalResponse: UseChatHelpers<ChatMessage>["addToolApprovalResponse"];
  input: string;
  setInput: Dispatch<SetStateAction<string>>;
  visibilityType: VisibilityType;
  isReadonly: boolean;
  isLoading: boolean;
  votes: Vote[] | undefined;
  currentModelId: string;
  setCurrentModelId: (id: string) => void;
  showCreditCardAlert: boolean;
  setShowCreditCardAlert: Dispatch<SetStateAction<boolean>>;
};

const ActiveChatContext = createContext<ActiveChatContextValue | null>(null);

function extractChatId(pathname: string): string | null {
  const match = pathname.match(/\/chat\/([^/]+)/);
  return match ? match[1] : null;
}

export function ActiveChatProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { setDataStream } = useDataStream();
  const { mutate } = useSWRConfig();

  const chatIdFromUrl = extractChatId(pathname);
  const isNewChat = !chatIdFromUrl;
  const newChatIdRef = useRef(generateUUID());
  const prevPathnameRef = useRef(pathname);

  if (isNewChat && prevPathnameRef.current !== pathname) {
    newChatIdRef.current = generateUUID();
  }
  prevPathnameRef.current = pathname;

  const chatId = chatIdFromUrl ?? newChatIdRef.current;

  const [currentModelId, setCurrentModelId] = useState(DEFAULT_CHAT_MODEL);
  console.log("[useActiveChat] currentModelId:", currentModelId);
  const currentModelIdRef = useRef(currentModelId);
  useEffect(() => {
    currentModelIdRef.current = currentModelId;
  }, [currentModelId]);

  const [input, setInput] = useState("");
  const [showCreditCardAlert, setShowCreditCardAlert] = useState(false);

  // Ensure demo user exists in DB
  useEffect(() => {
    ensureUser().catch(() => {});
  }, []);

  const { data: chatData, isLoading } = useSWR(
    isNewChat
      ? null
      : `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/messages?chatId=${chatId}`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const initialMessages: ChatMessage[] = isNewChat
    ? []
    : (chatData?.messages ?? []);
  const visibility: VisibilityType = isNewChat
    ? "private"
    : (chatData?.visibility ?? "private");

  const chatExistsRef = useRef(false);
  useEffect(() => {
    if (chatData) {
      chatExistsRef.current = true;
    }
  }, [chatData]);

  const {
    messages,
    setMessages,
    sendMessage: rawSendMessage,
    status,
    error: chatError,
    stop,
    regenerate,
    resumeStream,
    addToolApprovalResponse,
  } = useChat<ChatMessage>({
    id: chatId,
    messages: initialMessages,
    generateId: generateUUID,
    sendAutomaticallyWhen: ({ messages: currentMessages }) => {
      const lastMessage = currentMessages.at(-1);
      return (
        lastMessage?.parts?.some(
          (part) =>
            "state" in part &&
            part.state === "approval-responded" &&
            "approval" in part &&
            (part.approval as { approved?: boolean })?.approved === true
        ) ?? false
      );
    },
    transport: new TextStreamChatTransport({
      api: `${process.env.NEXT_PUBLIC_BACKEND_URL ?? ""}/chat`,
      fetch: fetchWithErrorHandlers,
      prepareSendMessagesRequest(request) {
        // Use the chatId (request.id) as the stable session_id so follow-ups
        // are always tied to the same backend session.
        const session_id = request.id;

        // Convert AI SDK message format (parts) to backend format (content)
        const messages = request.messages.map((msg) => {
          const text = msg.parts
            ?.filter((p: any) => p.type === "text")
            .map((p: any) => p.text)
            .join("");
          return { role: msg.role, content: text || "" };
        });

        return {
          body: {
            messages,
            session_id,
            model: currentModelIdRef.current,
          },
        };
      },
    }),
    onData: (dataPart) => {
      console.log("[useChat] onData:", dataPart);
      setDataStream((ds) => (ds ? [...ds, dataPart] : []));
    },
    onFinish: async ({ message }) => {
      console.log("[useChat] onFinish, message:", message);

      // Persist assistant message
      try {
        await createMessages({
          messages: [
            {
              id: message.id,
              chatId,
              role: message.role,
              parts: message.parts,
              createdAt: new Date().toISOString(),
            },
          ],
        });
      } catch {
        // ignore persistence errors
      }

      mutate(unstable_serialize(getChatHistoryPaginationKey));
    },
    onError: (error) => {
      console.error("[useChat] onError:", error);
      if (error.message?.includes("AI Gateway requires a valid credit card")) {
        setShowCreditCardAlert(true);
      } else if (error instanceof ChatbotError) {
        toast({ type: "error", description: error.message });
      } else {
        toast({
          type: "error",
          description: error.message || "Oops, an error occurred!",
        });
      }
    },
  });

  // Wrap sendMessage to persist chat and user message
  const sendMessage = useMemo(() => {
    return async (message: Parameters<typeof rawSendMessage>[0]) => {
      const msg = message as ChatMessage;
      // Ensure message has an ID so useChat and DB stay in sync
      if (!msg.id) {
        (msg as any).id = generateUUID();
      }

      let title = "New chat";
      try {
        title = await generateTitleFromUserMessage({
          message: { parts: msg.parts },
        });
      } catch {
        // fallback title
      }

      // Create chat if it doesn't exist yet
      if (!chatExistsRef.current) {
        try {
          await createChat({
            id: chatId,
            title,
            userId: "00000000-0000-0000-0000-000000000001",
            visibility: "private",
          });
          chatExistsRef.current = true;
        } catch {
          // ignore
        }
      }

      // Persist user message
      try {
        await createMessages({
          messages: [
            {
              id: msg.id,
              chatId,
              role: msg.role,
              parts: msg.parts,
              createdAt: new Date().toISOString(),
            },
          ],
        });
      } catch {
        // ignore persistence errors
      }

      console.log("[sendMessage] calling rawSendMessage");
      return rawSendMessage(message);
    };
  }, [rawSendMessage, chatId]);

  const loadedChatIds = useRef(new Set<string>());

  if (isNewChat && !loadedChatIds.current.has(newChatIdRef.current)) {
    loadedChatIds.current.add(newChatIdRef.current);
  }

  useEffect(() => {
    console.log("[useChat] status:", status, "messages count:", messages.length);
  }, [status, messages]);

  useEffect(() => {
    if (loadedChatIds.current.has(chatId)) {
      return;
    }
    // Only load messages from DB if the chat actually exists (userId != null).
    // This prevents clearing locally-added messages for new chats that haven't
    // been persisted yet.
    if (chatData?.userId != null) {
      loadedChatIds.current.add(chatId);
      setMessages(chatData.messages ?? []);
    }
  }, [chatId, chatData, setMessages]);

  const prevChatIdRef = useRef(chatId);
  useEffect(() => {
    if (prevChatIdRef.current !== chatId) {
      prevChatIdRef.current = chatId;
      chatExistsRef.current = false;
      if (isNewChat) {
        setMessages([]);
      }
    }
  }, [chatId, isNewChat, setMessages]);

  useEffect(() => {
    if (chatData && !isNewChat) {
      const cookieModel = document.cookie
        .split("; ")
        .find((row) => row.startsWith("chat-model="))
        ?.split("=")[1];
      if (cookieModel) {
        setCurrentModelId(decodeURIComponent(cookieModel));
      }
    }
  }, [chatData, isNewChat]);

  // Fetch available models and ensure current model is valid
  const { data: modelsData } = useSWR(
    `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/models`,
    fetcher,
    { revalidateOnFocus: false }
  );

  useEffect(() => {
    if (!modelsData) return;
    const availableIds = new Set<string>(
      modelsData.available_model_ids ?? []
    );
    const backendDefault = modelsData.default_model ?? DEFAULT_CHAT_MODEL;

    // If current model is not available, switch to backend default
    if (availableIds.size > 0 && !availableIds.has(currentModelId)) {
      setCurrentModelId(backendDefault);
      setCookie("chat-model", backendDefault);
    }
  }, [modelsData, currentModelId]);

  const hasAppendedQueryRef = useRef(false);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("query");
    if (query && !hasAppendedQueryRef.current) {
      hasAppendedQueryRef.current = true;
      window.history.replaceState(
        {},
        "",
        `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/chat/${chatId}`
      );
      sendMessage({
        role: "user" as const,
        parts: [{ type: "text", text: query }],
      });
    }
  }, [sendMessage, chatId]);

  useAutoResume({
    autoResume: false,
    initialMessages,
    resumeStream,
    setMessages,
  });

  const isReadonly = isNewChat ? false : (chatData?.isReadonly ?? false);

  const { data: votes } = useSWR<Vote[]>(
    !isReadonly && messages.length >= 2
      ? `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/api/vote?chatId=${chatId}`
      : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const value = useMemo<ActiveChatContextValue>(
    () => ({
      chatId,
      messages,
      setMessages,
      sendMessage,
      status,
      error: chatError,
      stop,
      regenerate,
      addToolApprovalResponse,
      input,
      setInput,
      visibilityType: visibility,
      isReadonly,
      isLoading: !isNewChat && isLoading,
      votes,
      currentModelId,
      setCurrentModelId,
      showCreditCardAlert,
      setShowCreditCardAlert,
    }),
    [
      chatId,
      messages,
      setMessages,
      sendMessage,
      status,
      chatError,
      stop,
      regenerate,
      addToolApprovalResponse,
      input,
      visibility,
      isReadonly,
      isNewChat,
      isLoading,
      votes,
      currentModelId,
      showCreditCardAlert,
    ]
  );

  return (
    <ActiveChatContext.Provider value={value}>
      {children}
    </ActiveChatContext.Provider>
  );
}

export function useActiveChat() {
  const context = useContext(ActiveChatContext);
  if (!context) {
    throw new Error("useActiveChat must be used within ActiveChatProvider");
  }
  return context;
}
