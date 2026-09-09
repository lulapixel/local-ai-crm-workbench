import { useState } from "react";
import type { DailyActionItem } from "../types";

export function useDailyExecution(items: DailyActionItem[]) {
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);

  const startSession = () => {
    setIsSessionActive(true);
    setCurrentIndex(0);
    setCompletedCount(0);
  };

  const endSession = () => {
    setIsSessionActive(false);
    setCurrentIndex(0);
  };

  const nextAction = () => {
    if (currentIndex < items.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      endSession();
    }
  };

  const previousAction = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  const markCurrentCompleted = () => {
    setCompletedCount((prev) => prev + 1);
    nextAction();
  };

  const currentItem = items[currentIndex] || null;

  return {
    isSessionActive,
    currentIndex,
    totalCount: items.length,
    completedCount,
    currentItem,
    startSession,
    endSession,
    nextAction,
    previousAction,
    markCurrentCompleted,
  };
}
