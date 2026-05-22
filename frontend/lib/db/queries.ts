/* eslint-disable @typescript-eslint/no-explicit-any */
import { createClient } from "@/utils/supabase/server";
import { generateDummyPassword } from "./utils";

export async function getUser(email: string): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("User")
    .select("*")
    .eq("email", email);
  if (error) throw error;
  return data ?? [];
}

export async function getUserById(id: string): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("User")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data ?? null;
}

export async function createUser(
  email: string,
  password: string
): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("User")
    .insert({ email, password })
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function createGuestUser(): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("User")
    .insert({
      email: "guest@basis.ai",
      isAnonymous: true,
      password: generateDummyPassword(),
    })
    .select()
    .single();
  if (error) throw error;
  return [data];
}

export async function saveChat(chat: any): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Chat")
    .insert(chat)
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function deleteChatById({ id }: { id: string }): Promise<any> {
  const supabase = await createClient();
  await supabase.from("Vote_v2").delete().eq("chatId", id);
  await supabase.from("Message_v2").delete().eq("chatId", id);
  await supabase.from("Stream").delete().eq("chatId", id);
  const { error } = await supabase.from("Chat").delete().eq("id", id);
  if (error) throw error;
  return { id };
}

export async function deleteAllChatsByUserId(_args: any): Promise<any> {
  const supabase = await createClient();
  const { userId } = _args;
  const { data: chats } = await supabase
    .from("Chat")
    .select("id")
    .eq("userId", userId);
  const ids = chats?.map((c: any) => c.id) ?? [];
  if (ids.length > 0) {
    await supabase.from("Vote_v2").delete().in("chatId", ids);
    await supabase.from("Message_v2").delete().in("chatId", ids);
    await supabase.from("Stream").delete().in("chatId", ids);
    await supabase.from("Chat").delete().in("id", ids);
  }
}

export async function getChatsByUserId(_args: any): Promise<any> {
  const supabase = await createClient();
  const { id, limit = 10, startingAfter, endingBefore } = _args;
  let query = supabase
    .from("Chat")
    .select("*")
    .eq("userId", id)
    .order("createdAt", { ascending: false })
    .limit(limit + 1);

  if (startingAfter) {
    query = query.lt("createdAt", startingAfter);
  }

  if (endingBefore) {
    query = query.gt("createdAt", endingBefore);
  }

  const { data, error } = await query;
  if (error) throw error;

  const chats = data ?? [];
  const hasMore = chats.length > limit;
  if (hasMore) chats.pop();

  return { chats, hasMore };
}

export async function getChatById({ id }: { id: string }): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Chat")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data ?? null;
}

export async function saveMessages({
  messages,
}: {
  messages: any[];
}): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Message_v2")
    .insert(messages)
    .select();
  if (error) throw error;
  return data ?? messages;
}

export async function updateMessage({
  id,
  parts,
}: {
  id: string;
  parts: any;
}): Promise<any> {
  const supabase = await createClient();
  const { error } = await supabase
    .from("Message_v2")
    .update({ parts })
    .eq("id", id);
  if (error) throw error;
  return { id, parts };
}

export async function getMessagesByChatId({
  id,
}: {
  id: string;
}): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Message_v2")
    .select("*")
    .eq("chatId", id)
    .order("createdAt", { ascending: true });
  if (error) throw error;
  return data ?? [];
}

export async function getMessageById({ id }: { id: string }): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Message_v2")
    .select("*")
    .eq("id", id);
  if (error) throw error;
  return data ?? [];
}

export async function voteMessage({
  chatId,
  messageId,
  type,
}: any): Promise<any> {
  const supabase = await createClient();
  const { error } = await supabase.from("Vote_v2").upsert({
    chatId,
    messageId,
    isUpvoted: type === "up",
  });
  if (error) throw error;
  return {};
}

export async function getVotesByChatId({ id }: { id: string }): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Vote_v2")
    .select("*")
    .eq("chatId", id);
  if (error) throw error;
  return data ?? [];
}

export async function saveDocument({
  id,
  title,
  kind,
  content,
  userId,
}: any): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Document")
    .insert({ id, title, kind, content, userId, createdAt: new Date().toISOString() })
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function updateDocumentContent({ id, content }: any): Promise<any> {
  const supabase = await createClient();
  const { data: latest, error: selectError } = await supabase
    .from("Document")
    .select("createdAt")
    .eq("id", id)
    .order("createdAt", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (selectError) throw selectError;
  if (!latest) return { id, content };

  const { error: updateError } = await supabase
    .from("Document")
    .update({ content })
    .eq("id", id)
    .eq("createdAt", latest.createdAt);

  if (updateError) throw updateError;
  return { id, content };
}

export async function getDocumentsById({ id }: { id: string }): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Document")
    .select("*")
    .eq("id", id)
    .order("createdAt", { ascending: false });
  if (error) throw error;
  return data ?? [];
}

export async function getDocumentById({ id }: { id: string }): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Document")
    .select("*")
    .eq("id", id)
    .order("createdAt", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return data ?? null;
}

export async function deleteDocumentsByIdAfterTimestamp({
  id,
  timestamp,
}: any): Promise<any> {
  const supabase = await createClient();
  const ts =
    timestamp instanceof Date ? timestamp.toISOString() : new Date(timestamp).toISOString();
  const { error } = await supabase
    .from("Document")
    .delete()
    .eq("id", id)
    .gt("createdAt", ts);
  if (error) throw error;
}

export async function saveSuggestions({ suggestions }: any): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Suggestion")
    .insert(suggestions)
    .select();
  if (error) throw error;
  return data ?? suggestions;
}

export async function getSuggestionsByDocumentId({
  documentId,
}: {
  documentId: string;
}): Promise<any> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("Suggestion")
    .select("*")
    .eq("documentId", documentId);
  if (error) throw error;
  return data ?? [];
}

export async function getMessageCountByUserId({
  id,
  differenceInHours,
}: any): Promise<any> {
  const supabase = await createClient();
  const since = new Date(
    Date.now() - differenceInHours * 60 * 60 * 1000
  ).toISOString();

  const { data: chatIds, error: chatError } = await supabase
    .from("Chat")
    .select("id")
    .eq("userId", id);

  if (chatError) throw chatError;
  if (!chatIds || chatIds.length === 0) return 0;

  const { count, error } = await supabase
    .from("Message_v2")
    .select("*", { count: "exact", head: true })
    .in(
      "chatId",
      chatIds.map((c: any) => c.id)
    )
    .gte("createdAt", since);

  if (error) throw error;
  return count ?? 0;
}

export async function updateChatTitleById({ chatId, title }: any): Promise<any> {
  const supabase = await createClient();
  const { error } = await supabase
    .from("Chat")
    .update({ title })
    .eq("id", chatId);
  if (error) throw error;
  return { chatId, title };
}

export async function createStreamId({ streamId, chatId }: any): Promise<any> {
  const supabase = await createClient();
  const { error } = await supabase
    .from("Stream")
    .insert({ id: streamId, chatId, createdAt: new Date().toISOString() });
  if (error) throw error;
}

export async function deleteMessagesByChatIdAfterTimestamp({
  chatId,
  timestamp,
}: any): Promise<any> {
  const supabase = await createClient();
  const ts =
    timestamp instanceof Date ? timestamp.toISOString() : new Date(timestamp).toISOString();

  const { data: messages } = await supabase
    .from("Message_v2")
    .select("id")
    .eq("chatId", chatId)
    .gt("createdAt", ts);

  const msgIds = messages?.map((m: any) => m.id) ?? [];
  if (msgIds.length > 0) {
    await supabase.from("Vote_v2").delete().in("messageId", msgIds);
  }

  const { error } = await supabase
    .from("Message_v2")
    .delete()
    .eq("chatId", chatId)
    .gt("createdAt", ts);
  if (error) throw error;
}

export async function updateChatVisibilityById({
  chatId,
  visibility,
}: any): Promise<any> {
  const supabase = await createClient();
  const { error } = await supabase
    .from("Chat")
    .update({ visibility })
    .eq("id", chatId);
  if (error) throw error;
  return { chatId, visibility };
}
