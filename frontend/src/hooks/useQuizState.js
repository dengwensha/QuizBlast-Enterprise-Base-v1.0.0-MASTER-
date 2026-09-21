import { useRef, useState } from "react";

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
  const [selectedQuizIdState, setSelectedQuizIdState] = useState("");
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const selectedQuizIdRef = useRef("");
  const questionRequestRef = useRef(0);
  const quizListRequestRef = useRef(0);

  selectedQuizIdRef.current = selectedQuizIdState;

  const setSelectedQuizId = (id) => {
    const nextId = String(id || "");
    selectedQuizIdRef.current = nextId;
    questionRequestRef.current += 1;
    setSelectedQuizIdState(nextId);
    setSelectedQuestions([]);
  };

  const loadQuizzes = async () => {
    const request = ++quizListRequestRef.current;
    const list = await fetchQuizzes(user);

    if (request !== quizListRequestRef.current) {
      return list;
    }

    setQuizzes(list);

    if (list.length > 0 && !selectedQuizIdRef.current) {
      setSelectedQuizId(String(list[0].id));
    }

    return list;
  };

  const loadSelectedQuestions = async (id) => {
    const targetId = String(id || "");
    const request = ++questionRequestRef.current;

    if (!targetId) {
      if (request === questionRequestRef.current) {
        setSelectedQuestions([]);
      }
      return [];
    }

    const list = await fetchQuizQuestions(user, targetId);

    if (
      request !== questionRequestRef.current ||
      selectedQuizIdRef.current !== targetId
    ) {
      return list;
    }

    setSelectedQuestions(list);
    return list;
  };

  const refreshSelectedQuiz = async (quizId = selectedQuizIdRef.current) => {
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
    const quizId = selectedQuizIdRef.current;

    if (!quizId) {
      return;
    }

    await deleteQuizRequest(user, quizId);

    setSelectedQuizId("");

    await loadQuizzes();
  };

  const addQuestionRequestState = async (payload) => {
    const data = await addQuestionRequest(
      user,
      selectedQuizIdRef.current,
      payload
    );

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
    quizListRequestRef.current += 1;
    questionRequestRef.current += 1;
    selectedQuizIdRef.current = "";
    setQuizzes([]);
    setSelectedQuizIdState("");
    setSelectedQuestions([]);
  };

  return {
    quizzes,
    selectedQuizId: selectedQuizIdState,
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