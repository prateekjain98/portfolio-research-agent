import type {
  UIMessage,
  UIMessagePart,
} from 'ai';
import { type ClassValue, clsx } from 'clsx';
import { formatISO } from 'date-fns';
import { twMerge } from 'tailwind-merge';
import type { DBMessage, Document } from '@/lib/db/schema';
import { ChatbotError, type ErrorCode } from './errors';
import type { ChatMessage, ChatTools, CustomUIDataTypes } from './types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

let _nativeFetch: typeof fetch | null = null;

export function getNativeFetch(): typeof fetch {
  if (typeof window === 'undefined') return fetch;
  if (_nativeFetch) return _nativeFetch;
  try {
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
    const win = iframe.contentWindow;
    if (win && win.fetch !== window.fetch) {
      _nativeFetch = win.fetch.bind(win);
      // Keep the iframe in the DOM so its global scope doesn't shut down.
      // Hidden and inaccessible, it provides a clean fetch reference.
      return _nativeFetch;
    }
    document.body.removeChild(iframe);
  } catch {
    // ignore
  }
  _nativeFetch = fetch;
  return _nativeFetch;
}

export const fetcher = async (url: string) => {
  const doFetch = typeof window !== 'undefined' ? getNativeFetch() : fetch;
  const response = await doFetch(url);

  if (!response.ok) {
    const { code, cause } = await response.json();
    throw new ChatbotError(code as ErrorCode, cause);
  }

  return response.json();
};

export async function fetchWithErrorHandlers(
  input: RequestInfo | URL,
  init?: RequestInit,
) {
  const doFetch = typeof window !== 'undefined' ? getNativeFetch() : fetch;
  try {
    const response = await doFetch(input, init);

    if (!response.ok) {
      const text = await response.text();
      try {
        const { code, cause } = JSON.parse(text);
        throw new ChatbotError(code as ErrorCode, cause);
      } catch {
        throw new ChatbotError('offline:chat', text.slice(0, 200));
      }
    }

    return response;
  } catch (error: unknown) {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      throw new ChatbotError('offline:chat');
    }

    throw error;
  }
}

export function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function getDocumentTimestampByIndex(
  documents: Document[],
  index: number,
) {
  if (!documents) { return new Date(); }
  if (index > documents.length) { return new Date(); }

  return documents[index].createdAt;
}

export function sanitizeText(text: string) {
  return text.replace('<has_function_call>', '');
}

export function convertToUIMessages(messages: DBMessage[]): ChatMessage[] {
  return messages.map((message) => ({
    id: message.id,
    role: message.role as 'user' | 'assistant' | 'system',
    parts: message.parts as UIMessagePart<CustomUIDataTypes, ChatTools>[],
    metadata: {
      createdAt: formatISO(message.createdAt),
    },
  }));
}

export function getTextFromMessage(message: ChatMessage | UIMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => (part as { type: 'text'; text: string}).text)
    .join('');
}
