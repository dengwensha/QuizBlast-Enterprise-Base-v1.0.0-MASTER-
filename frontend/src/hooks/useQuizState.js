import { useState } from "react";

import {
  fetchQuizzes,
  fetchQuizQuestions,
  createQuizRequest,
  deleteQuizRequest,
  addQuestionRequest,
  deleteQuestionRequest,
  updateQuestionRequest,
} from "../services/quizService";

export function useQuizState(user) {
  const [quizzes, setQuizzes] = useState([]);
  const [selectedQuizId, setSelectedQuizId] = useState("");
  const [selectedQuestions, setSelectedQuestions] = useState([]);

  const loadQuizzes = async () => {
    const list = await fetchQuizzes(user);

    setQuizzes(list);

    if (list.length > 0 && !selectedQuizId) {
      setSelectedQuizId(String(list[0].id));
    }

    return list;
  };

  const loadSelectedQuestions = async (id) => {
    if (!id) {
      setSelectedQuestions([]);
      return [];
    }

    const list = await fetchQuizQuestions(user, id);
    setSelectedQuestions(list);
    return list;
  };

  const refreshSelectedQuiz = async (quizId = selectedQuizId) => {
    await loadQuizzes();

    if (quizId) {
      await loadSelectedQuestions(quizId);
    }
  };

  const createQuizRequestState = async (title) => {
    const data = await createQuizRequest(user, title);

    if (data.error) {
      return data;
    }

    const createdQuizId = String(data.id);
    setSelectedQuizId(createdQuizId);

    await loadQuizzes();
    await loadSelectedQuestions(createdQuizId);

    return data;
  };

  const deleteQuizRequestState = async () => {
    if (!selectedQuizId) {
      return;
    }

    await deleteQuizRequest(user, selectedQuizId);

    setSelectedQuizId("");
    setSelectedQuestions([]);

    await loadQuizzes();
  };

  const addQuestionRequestState = async (payload) => {
    const data = await addQuestionRequest(user, selectedQuizId, payload);

    if (data.error) {
      return data;
    }

    await refreshSelectedQuiz();

    return data;
  };

  const deleteQuestionRequestState = async (questionId) => {
    await deleteQuestionRequest(user, questionId);
    await refreshSelectedQuiz();
  };

  const updateQuestionRequestState = async (questionId, payload) => {
    const data = await updateQuestionRequest(user, questionId, payload);

    if (data.error) {
      return data;
    }

    await refreshSelectedQuiz();

    return data;
  };

  const clearQuizState = () => {
    setQuizzes([]);
    setSelectedQuizId("");
    setSelectedQuestions([]);
  };

  return {
    quizzes,
    selectedQuizId,
    setSelectedQuizId,
    selectedQuestions,
    loadQuizzes,
    loadSelectedQuestions,
    createQuizRequestState,
    deleteQuizRequestState,
    addQuestionRequestState,
    deleteQuestionRequestState,
    updateQuestionRequestState,
    clearQuizState,
  };
}
