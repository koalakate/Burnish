import { create } from "zustand";
import type { Deck } from "@/lib/types";

interface DeckState {
  activeDeck: Deck | null;
  setActiveDeck: (deck: Deck | null) => void;
}

export const useDeckStore = create<DeckState>((set) => ({
  activeDeck: null,
  setActiveDeck: (deck) => set({ activeDeck: deck }),
}));
