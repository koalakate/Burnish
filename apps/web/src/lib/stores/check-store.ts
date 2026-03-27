import { create } from "zustand";
import type { CheckRun } from "@/lib/types";

interface CheckState {
  activeCheck: CheckRun | null;
  setActiveCheck: (check: CheckRun | null) => void;
}

export const useCheckStore = create<CheckState>((set) => ({
  activeCheck: null,
  setActiveCheck: (check) => set({ activeCheck: check }),
}));
