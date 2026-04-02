import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch, apiUpload } from "./api";
import type {
  Deck,
  CheckRunDetail,
  SlideDetail,
  CorrectionsResponse,
  ExportResponse,
} from "./types";

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

// ---- Check keys ----

export const checkKeys = {
  all: ["checks"] as const,
  detail: (id: string) => ["checks", id] as const,
  slide: (checkId: string, slideIndex: number) =>
    ["checks", checkId, "slides", slideIndex] as const,
};

// ---- Check queries ----

export function useCheckRun(checkRunId: string) {
  return useQuery({
    queryKey: checkKeys.detail(checkRunId),
    queryFn: () => apiFetch<CheckRunDetail>(`/api/checks/${checkRunId}`),
    enabled: !!checkRunId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "queued" || status === "running") return 2000;
      return false;
    },
  });
}

export function useSlideDetail(checkRunId: string, slideIndex: number) {
  return useQuery({
    queryKey: checkKeys.slide(checkRunId, slideIndex),
    queryFn: () =>
      apiFetch<SlideDetail>(
        `/api/checks/${checkRunId}/slides/${slideIndex}`
      ),
    enabled: !!checkRunId && slideIndex >= 0,
  });
}

// ---- Correction keys ----

export const correctionKeys = {
  all: (checkRunId: string) => ["corrections", checkRunId] as const,
  export: (checkRunId: string) => ["corrections", checkRunId, "export"] as const,
};

// ---- Correction queries ----

export function useCorrections(checkRunId: string) {
  return useQuery({
    queryKey: correctionKeys.all(checkRunId),
    queryFn: () =>
      apiFetch<CorrectionsResponse>(
        `/api/checks/${checkRunId}/corrections`
      ),
    enabled: !!checkRunId,
  });
}

// ---- Correction mutations ----

export function useAcceptCorrection(checkRunId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (correctionId: string) =>
      apiFetch<void>(
        `/api/checks/${checkRunId}/corrections/${correctionId}/accept`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: correctionKeys.all(checkRunId),
      });
    },
  });
}

export function useDismissCorrection(checkRunId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (correctionId: string) =>
      apiFetch<void>(
        `/api/checks/${checkRunId}/corrections/${correctionId}/dismiss`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: correctionKeys.all(checkRunId),
      });
    },
  });
}

export function useFixAll(checkRunId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      apiFetch<void>(`/api/checks/${checkRunId}/fix-all`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: correctionKeys.all(checkRunId),
      });
    },
  });
}

export function useExport(checkRunId: string, enabled: boolean) {
  return useQuery({
    queryKey: correctionKeys.export(checkRunId),
    queryFn: () =>
      apiFetch<ExportResponse>(`/api/checks/${checkRunId}/export`),
    enabled: !!checkRunId && enabled,
  });
}
