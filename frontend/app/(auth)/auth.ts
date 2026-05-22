export type UserType = "guest" | "regular";

const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

export const auth = async () => {
  return {
    user: {
      id: DEMO_USER_ID,
      email: "demo@basis.ai",
      name: "Demo User",
      type: "regular" as UserType,
    },
  };
};

export const signIn = async (_provider?: string, _options?: any) => ({ error: null });
export const signOut = async (_options?: any) => {};
