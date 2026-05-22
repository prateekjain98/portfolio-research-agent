import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// NOTE: In-memory map won't persist across serverless invocations.
const chatToSession = new Map<string, string>();

export async function POST(request: Request) {
  const body = await request.json();
  const chatId = body.id as string | undefined;

  let messages: Array<{ role: string; content: string }> = [];

  if (body.message && Array.isArray(body.message.parts)) {
    const textParts = body.message.parts
      .filter((p: any) => p.type === "text")
      .map((p: any) => p.text);
    const content = textParts.join("");
    messages = [{ role: "user", content }];
  } else if (body.messages && Array.isArray(body.messages)) {
    messages = body.messages.map((msg: any) => {
      if (msg.parts && Array.isArray(msg.parts)) {
        const text = msg.parts
          .filter((p: any) => p.type === "text")
          .map((p: any) => p.text)
          .join("");
        return { role: msg.role, content: text };
      }
      return { role: msg.role, content: msg.content || "" };
    });
  }

  const sessionId = chatId ? chatToSession.get(chatId) : undefined;

  const backendBody = {
    messages,
    session_id: sessionId || null,
  };

  const backendRes = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(backendBody),
  });

  if (!backendRes.ok) {
    const text = await backendRes.text();
    return NextResponse.json(
      { code: "offline:chat", message: "Backend error", cause: text },
      { status: backendRes.status }
    );
  }

  const reader = backendRes.body?.getReader();
  const decoder = new TextDecoder();
  let sessionIdCaptured = false;

  const stream = new ReadableStream({
    async start(controller) {
      if (!reader) {
        controller.close();
        return;
      }
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });

        if (!sessionIdCaptured && chatId && !sessionId) {
          const match = chunk.match(/\*\*Thesis ID:\*\* `([a-f0-9]+)`/);
          if (match) {
            chatToSession.set(chatId, match[1]);
            sessionIdCaptured = true;
          }
        }

        controller.enqueue(value);
      }
      controller.close();
    },
  });

  return new NextResponse(stream, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
