import { useLayoutEffect, useRef, useState } from "react";
function useAdminState({
  user,
  selectedQuizId,
  createQuizRequestState,
  deleteQuizRequestState,
  addQuestionRequestState,
  deleteQuestionRequestState,
  updateQuestionRequestState,
  loadQuizzes,
  loadSelectedQuestions
}) {
  const [newQuizTitle, setNewQuizTitle] = useState("");
  const [newQuestion, setNewQuestion] = useState("");
  const [newImageUrl, setNewImageUrl] = useState("");
  const [newOptions, setNewOptions] = useState(["", "", "", ""]);
  const [newCorrect, setNewCorrect] = useState(0);
  const [newTime, setNewTime] = useState(15);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiAudience, setAiAudience] = useState("Serbest");
  const [aiCount, setAiCount] = useState(5);
  const [aiDifficulty, setAiDifficulty] = useState("Orta");
  const [aiQuestionType, setAiQuestionType] = useState("Çoktan Seçmeli");
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiPreviewQuestions, setAiPreviewQuestions] = useState([]);
  const aiAddInProgressRef = useRef(false);

  useLayoutEffect(() => {
    setNewQuizTitle("");
    setNewQuestion("");
    setNewImageUrl("");
    setNewOptions(["", "", "", ""]);
    setNewCorrect(0);
    setNewTime(15);
    setAiPrompt("");
    setAiAudience("Serbest");
    setAiCount(5);
    setAiDifficulty("Orta");
    setAiQuestionType("Çoktan Seçmeli");
    setAiInstruction("");
    setAiPreviewQuestions([]);
    aiAddInProgressRef.current = false;
  }, [user?.email, user?.token]);
  const createQuiz = async () => {
    if (!newQuizTitle.trim()) {
      return alert("Quiz adı gir.");
    }
    const d = await createQuizRequestState(newQuizTitle);
    if (d.error) {
      return alert(d.error);
    }
    setNewQuizTitle("");
  };
  const deleteQuiz = async () => {
    if (!selectedQuizId) {
      return alert("Quiz seç.");
    }
    if (!confirm("Bu quiz ve tüm sorular silinsin mi?")) {
      return;
    }
    await deleteQuizRequestState();
  };
  const addQuestion = async (q = newQuestion, img = newImageUrl, opts = newOptions, c = Number(newCorrect), tm = Number(newTime)) => {
    if (!selectedQuizId) return alert("Quiz seç");
    if (!q.trim()) return alert("Soru gir.");
    if (opts.some((o) => !String(o).trim()))
      return alert("4 seçeneği de doldur.");
    const d = await addQuestionRequestState({
      question: q,
      image_url: img,
      options: opts,
      correct: c,
      time: tm
    });
    if (d.error) return alert(d.error);
    setNewQuestion("");
    setNewImageUrl("");
    setNewOptions(["", "", "", ""]);
    setNewCorrect(0);
    setNewTime(15);
  };
  const generateMockAiQuestions = () => {
    if (!String(aiPrompt || "").trim()) return alert("Konu / Prompt alanı boş olamaz.");
    const multipleChoiceTemplates = [{ question: "What is the most important point about this topic?", options: ["Basic rule", "Wrong approach", "Unrelated detail", "No rule"], correct: 0 }, { question: "Which option is the best practice?", options: ["Ignore instructions", "Follow the correct procedure", "Guess quickly", "Skip preparation"], correct: 1 }, { question: "What should participants remember?", options: ["The key rule", "A random number", "An unrelated name", "Nothing"], correct: 0 }, { question: "Which statement is correct?", options: ["Preparation is important", "Rules are unnecessary", "Mistakes never happen", "Training has no value"], correct: 0 }, { question: "What is the best response in a risky situation?", options: ["Stop and check", "Continue without thinking", "Ignore warnings", "Hide the problem"], correct: 0 }];
    const trueFalseTemplates = [{ question: "Following instructions is important for this topic.", options: ["True", "False", "True and False", "Not sure"], correct: 0 }, { question: "Preparation is unnecessary for this topic.", options: ["True", "False", "True and False", "Not sure"], correct: 1 }, { question: "Participants should understand the basic rules.", options: ["True", "False", "True and False", "Not sure"], correct: 0 }];
    const count = Math.min(Math.max(Number(aiCount) || 1, 1), 20);
    const generated = [];
    for (let i = 0; i < count; i++) {
      let pool = multipleChoiceTemplates;
      if (aiQuestionType === "Doğru / Yanlış") pool = trueFalseTemplates;
      if (aiQuestionType === "Karışık") pool = i % 2 === 0 ? multipleChoiceTemplates : trueFalseTemplates;
      const b = pool[i % pool.length];
      generated.push({ question: b.question, image_url: "", options: b.options, correct: b.correct, time: Number(newTime || 15) });
    }
    setAiPreviewQuestions(generated);
    alert(`${count} adet soru önizlemeye hazırlandı. Henüz quiz’e eklenmedi.`);
  };
  const addAiPreviewToQuiz = async () => {
    if (!selectedQuizId) return alert("Önce quiz seç.");
    if (aiPreviewQuestions.length === 0) return alert("Önce AI soruları oluştur.");
    if (aiAddInProgressRef.current) return;

    aiAddInProgressRef.current = true;
    const previewAtStart = [...aiPreviewQuestions];
    const failedQuestions = [];
    let importedCount = 0;

    try {
      for (const q of previewAtStart) {
        try {
          const d = await addQuestionRequestState({
            question: q.question,
            image_url: q.image_url || "",
            options: q.options,
            correct: q.correct,
            time: q.time
          });

          if (d?.error) {
            failedQuestions.push({ ...q, error: d.error });
          } else {
            importedCount += 1;
          }
        } catch (error) {
          console.error(error);
          failedQuestions.push({ ...q, error: "request_failed" });
        }
      }

      if (importedCount > 0) {
        await loadQuizzes();
        await loadSelectedQuestions(selectedQuizId);
      }

      setAiPreviewQuestions(failedQuestions);

      if (failedQuestions.length === 0) {
        alert(`${importedCount} AI sorusu quiz’e eklendi.`);
      } else if (importedCount === 0) {
        alert("AI soruları eklenemedi. Önizleme korunuyor; tekrar deneyebilirsin.");
      } else {
        alert(`${importedCount} soru eklendi, ${failedQuestions.length} soru eklenemedi. Başarısız sorular önizlemede tutuldu.`);
      }
    } finally {
      aiAddInProgressRef.current = false;
    }
  };
  const removeAiPreviewQuestion = (index) => setAiPreviewQuestions(aiPreviewQuestions.filter((_, i) => i !== index));
  const editAiPreviewQuestion = (index) => {
    const q = aiPreviewQuestions[index];
    if (!q) return;
    const qt = prompt("Soru metni:", q.question);
    if (qt === null) return;
    const opts = [...q.options];
    for (let i = 0; i < 4; i++) {
      const v = prompt(`Seçenek ${i + 1}:`, opts[i]);
      if (v === null) return;
      opts[i] = v;
    }
    const corr = Number(prompt("Doğru cevap indexi: A=0, B=1, C=2, D=3", q.correct));
    const tm = Number(prompt("Süre:", q.time));
    const u = [...aiPreviewQuestions];
    u[index] = { ...q, question: qt, options: opts, correct: Number.isNaN(corr) ? q.correct : Math.min(Math.max(corr, 0), 3), time: Number.isNaN(tm) ? q.time : tm };
    setAiPreviewQuestions(u);
  };
  const regenerateAiPreviewQuestion = (index) => {
    if (!String(aiPrompt || "").trim()) return alert("Konu / Prompt alanı boş olamaz.");
    const templates = [{ question: "Which answer best matches this topic?", options: ["The correct principle", "Unrelated answer", "Random guess", "No answer"], correct: 0 }, { question: "What is a useful reminder?", options: ["Check the key point", "Ignore the topic", "Avoid learning", "Skip all steps"], correct: 0 }, { question: "Which behavior is recommended?", options: ["Careful action", "Careless action", "No preparation", "Ignoring feedback"], correct: 0 }, { question: "True or False: Understanding the topic improves participation.", options: ["True", "False", "True and False", "Not sure"], correct: 0 }];
    const r = templates[Math.floor(Math.random() * templates.length)];
    const u = [...aiPreviewQuestions];
    u[index] = { question: r.question, image_url: "", options: r.options, correct: r.correct, time: Number(newTime || 15) };
    setAiPreviewQuestions(u);
  };
  const deleteQuestion = async (id) => {
    if (!confirm("Bu soru silinsin mi?")) return;
    await deleteQuestionRequestState(id);
  };
  const editQuestion = async (q) => {
    const question = prompt("Soru metni:", q.question);
    if (question === null) return;
    const options = [...q.options || ["", "", "", ""]];
    for (let i = 0; i < 4; i++) {
      const value = prompt(`Seçenek ${i + 1}:`, options[i] || "");
      if (value === null) return;
      options[i] = value;
    }
    const correct = Number(
      prompt("Doğru cevap indexi: A=0, B=1, C=2, D=3", q.correct)
    );
    const time = Number(prompt("Süre:", q.time || 15));
    const image_url = prompt("Görsel URL opsiyonel:", q.image_url || "");
    const payload = {
      question,
      image_url: image_url || "",
      options,
      correct: Number.isNaN(correct) ? q.correct : Math.min(Math.max(correct, 0), 3),
      time: Number.isNaN(time) ? q.time || 15 : time
    };
    const d = await updateQuestionRequestState(q.id, payload);
    if (d.error) return alert(d.error);
  };
  return {
    newQuizTitle,
    setNewQuizTitle,
    newQuestion,
    setNewQuestion,
    newImageUrl,
    setNewImageUrl,
    newOptions,
    setNewOptions,
    newCorrect,
    setNewCorrect,
    newTime,
    setNewTime,
    aiPrompt,
    setAiPrompt,
    aiAudience,
    setAiAudience,
    aiCount,
    setAiCount,
    aiDifficulty,
    setAiDifficulty,
    aiQuestionType,
    setAiQuestionType,
    aiInstruction,
    setAiInstruction,
    aiPreviewQuestions,
    setAiPreviewQuestions,
    createQuiz,
    deleteQuiz,
    addQuestion,
    generateMockAiQuestions,
    addAiPreviewToQuiz,
    removeAiPreviewQuestion,
    editAiPreviewQuestion,
    regenerateAiPreviewQuestion,
    deleteQuestion,
    editQuestion
  };
}
export {
  useAdminState
};