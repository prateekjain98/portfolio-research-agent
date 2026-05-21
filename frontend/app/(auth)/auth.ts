export type UserType = "guest" | "regular";

export const auth = async () => {
  return {
    user: {
      id: "demo-user",
      email: "demo@basis.ai",
      name: "Demo User",
      type: "regular" as UserType,
    },
  };
};

export const signIn = async (_provider?: string, _options?: any) => ({ error: null });
export const signOut = async (_options?: any) => {};

export async function GET() {
  return new Response(JSON.stringify({ user: { id: "demo", email: "demo@basis.ai" } }), {
    headers: { "Content-Type": "application/json" },
  });
}

export async function POST() {
  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
}
