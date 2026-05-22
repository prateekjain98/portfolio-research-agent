"use server";

import { cookies } from "next/headers";
import { auth } from "@/app/(auth)/auth";
import type { VisibilityType } from "@/components/chat/visibility-selector";
import {
  createUser,
  getUser,
  getUserById,
  saveChat,
  saveMessages,
  deleteMessagesByChatIdAfterTimestamp,
  getChatById,
  getMessageById,
  updateChatVisibilityById,
} from "@/lib/db/queries";

export async function saveChatModelAsCookie(model: string) {
  const cookieStore = await cookies();
  cookieStore.set("chat-model", model);
}

export async function ensureUser() {
  try {
    const session = await auth();
    if (!session?.user) return null;

    const existing = await getUser(session.user.email);
    if (existing && existing.length > 0) {
      return existing[0];
    }

    return await createUser(
      session.user.email,
      "demo-password",
      session.user.id
    );
  } catch (err) {
    console.warn("[ensureUser] Supabase error, returning mock user:", err);
    const session = await auth();
    return (
      session?.user ?? {
        id: "00000000-0000-0000-0000-000000000001",
        email: "demo@basis.ai",
      }
    );
  }
}

export async function createChat({
  id,
  title,
  userId,
  visibility = "private",
}: {
  id: string;
  title: string;
  userId: string;
  visibility?: VisibilityType;
}) {
  try {
    // Ensure user exists before creating chat (FK constraint)
    const existing = await getUserById(userId);
    if (!existing) {
      const session = await auth();
      if (session?.user?.email) {
        await createUser(session.user.email, "demo-password", userId);
      }
    }
    return await saveChat({
      id,
      title,
      userId,
      visibility,
      createdAt: new Date().toISOString(),
    });
  } catch (err) {
    console.warn("[createChat] Supabase error, returning mock chat:", err);
    return {
      id,
      title,
      userId,
      visibility,
      createdAt: new Date().toISOString(),
    };
  }
}

export async function createMessages({
  messages,
}: {
  messages: Array<{
    id: string;
    chatId: string;
    role: string;
    parts: any[];
    createdAt: string;
  }>;
}) {
  try {
    return await saveMessages({ messages });
  } catch (err) {
    console.warn("[createMessages] Supabase error, ignoring:", err);
    return messages;
  }
}

export async function generateTitleFromUserMessage({
  message,
}: {
  message: { parts?: Array<{ type: string; text?: string }> };
}) {
  const text =
    message.parts
      ?.filter((p) => p.type === "text")
      .map((p) => p.text)
      .join("") || "New chat";
  return text
    .slice(0, 40)
    .replace(/^[#*"\s]+/, "")
    .replace(/["]+$/, "")
    .trim();
}

export async function deleteTrailingMessages({ id }: { id: string }) {
  const session = await auth();
  if (!session?.user?.id) {
    throw new Error("Unauthorized");
  }

  const [message] = await getMessageById({ id });
  if (!message) {
    throw new Error("Message not found");
  }

  const chat = await getChatById({ id: message.chatId });
  if (!chat || chat.userId !== session.user.id) {
    throw new Error("Unauthorized");
  }

  await deleteMessagesByChatIdAfterTimestamp({
    chatId: message.chatId,
    timestamp: message.createdAt,
  });
}

export async function updateChatVisibility({
  chatId,
  visibility,
}: {
  chatId: string;
  visibility: VisibilityType;
}) {
  const session = await auth();
  if (!session?.user?.id) {
    throw new Error("Unauthorized");
  }

  const chat = await getChatById({ id: chatId });
  if (!chat || chat.userId !== session.user.id) {
    throw new Error("Unauthorized");
  }

  await updateChatVisibilityById({ chatId, visibility });
}
