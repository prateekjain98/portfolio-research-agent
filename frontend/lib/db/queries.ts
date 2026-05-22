// Stubs — no database in this demo
/* eslint-disable @typescript-eslint/no-explicit-any */

export async function getUser(email: string): Promise<any> { return []; }
export async function createUser(email: string, password: string): Promise<any> { return {}; }
export async function createGuestUser(): Promise<any> { return [{ id: "guest-1", email: "guest@basis.ai" }]; }
export async function saveChat(chat: any): Promise<any> { return chat; }
export async function deleteChatById({ id }: { id: string }): Promise<any> { return { id }; }
export async function deleteAllChatsByUserId(_args: any): Promise<any> { return; }
export async function getChatsByUserId(_args: any): Promise<any> { return { chats: [], hasMore: false }; }
export async function getChatById({ id }: { id: string }): Promise<any> {
  return null;
}
export async function saveMessages({ messages }: { messages: any[] }): Promise<any> { return messages; }
export async function updateMessage({ id, parts }: { id: string; parts: any }): Promise<any> { return { id, parts }; }
export async function getMessagesByChatId({ id }: { id: string }): Promise<any> { return []; }
export async function getMessageById({ id }: { id: string }): Promise<any> {
  return [];
}
export async function voteMessage({ chatId, messageId, type }: any): Promise<any> { return {}; }
export async function getVotesByChatId({ id }: { id: string }): Promise<any> { return []; }

export async function saveDocument({ id, title, kind, content, userId }: any): Promise<any> {
  return { id, userId };
}
export async function updateDocumentContent({ id, content }: any): Promise<any> { return { id, content }; }
export async function getDocumentsById({ id }: { id: string }): Promise<any> {
  return [];
}
export async function getDocumentById({ id }: { id: string }): Promise<any> { return null; }
export async function deleteDocumentsByIdAfterTimestamp({ id, timestamp }: any): Promise<any> { return; }
export async function saveSuggestions({ suggestions }: any): Promise<any> { return suggestions; }
export async function getSuggestionsByDocumentId({ documentId }: { documentId: string }): Promise<any> {
  return [];
}
export async function getMessageCountByUserId({ id, differenceInHours }: any): Promise<any> { return 0; }
export async function updateChatTitleById({ chatId, title }: any): Promise<any> { return { chatId, title }; }
export async function createStreamId({ streamId, chatId }: any): Promise<any> { return; }
export async function deleteMessagesByChatIdAfterTimestamp({ chatId, timestamp }: any): Promise<any> { return; }
export async function updateChatVisibilityById({ chatId, visibility }: any): Promise<any> { return { chatId, visibility }; }
