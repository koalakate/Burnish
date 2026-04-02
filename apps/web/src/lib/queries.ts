import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch, apiUpload } from "./api";
import type { Deck } from "./types";

// ---- Keys ----

export const deckKeys = {
  all: ["decks"] as const,
  detail: (id: string) => ["decks", id] as const,
};

// ---- Queries ----

export function useDecks() {
  return useQuery({
    queryKey: deckKeys.all,
    queryFn: () => apiFetch<{ decks: Deck[] }>("/api/decks"),
    select: (data) => data.decks,
  });
}

export function useDeck(id: string) {
  return useQuery({
    queryKey: deckKeys.detail(id),
    queryFn: () => apiFetch<Deck>(`/api/decks/${id}`),
    enabled: !!id,
  });
}

// ---- Mutations ----

export function useUploadDeck() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) =>
      apiUpload<{ deck_id: string }>("/api/decks/upload", file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deckKeys.all });
    },
  });
}

export function useDeleteDeck() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (deckId: string) =>
      apiFetch<void>(`/api/decks/${deckId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deckKeys.all });
    },
  });
}

export function useTriggerCheck() {
  return useMutation({
    mutationFn: (deckId: string) =>
      apiFetch<{ check_run_id: string }>(`/api/decks/${deckId}/check`, {
        method: "POST",
      }),
  });
}
