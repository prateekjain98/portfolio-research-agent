const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  let body: any;
  try {
    body = await request.json();
  } catch {
    return Response.json({ code: "bad_request", message: "Invalid JSON" }, { status: 400 });
  }

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

  const sessionId = body.session_id as string | undefined | null;

  const backendBody = {
    messages,
    session_id: sessionId || null,
  };

  try {
    const backendRes = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(backendBody),
    });

    if (!backendRes.ok) {
      const text = await backendRes.text();
      return Response.json(
        { code: "backend_error", message: "Backend error", cause: text.slice(0, 500) },
        { status: backendRes.status }
      );
    }

    return new Response(backendRes.body, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err: any) {
    return Response.json(
      { code: "backend_unreachable", message: "Cannot reach backend", cause: err.message },
      { status: 503 }
    );
  }
}
