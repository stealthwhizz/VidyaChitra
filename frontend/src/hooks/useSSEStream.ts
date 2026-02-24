import { useCallback, useRef, useState } from 'react';

export interface MCQ {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  is_diagram_based: boolean;
  prev_year_hint: boolean;
  marks: number;
}

export interface ShortAnswer {
  question: string;
  model_answer: string;
  marks: number;
  word_count_target: number;
  is_diagram_based: boolean;
}

export interface HOTQuestion {
  question: string;
  model_answer: string;
  marks: number;
  hint: string;
}

export interface QuestionsData {
  mcqs: MCQ[];
  short_answers: ShortAnswer[];
  hot_question: HOTQuestion;
  exam_tip: string;
}

export interface SSEStreamState {
  summary: string;
  chapterName: string;
  questions: QuestionsData | null;
  audioUrl: string | null;
  videoUrl: string | null;
  examTip: string;
  errors: { branch: string; msg: string }[];
  isLoading: boolean;
  isDone: boolean;
}

const initialState: SSEStreamState = {
  summary: '',
  chapterName: '',
  questions: null,
  audioUrl: null,
  videoUrl: null,
  examTip: '',
  errors: [],
  isLoading: false,
  isDone: false,
};

export function useSSEStream() {
  const [state, setState] = useState<SSEStreamState>(initialState);
  const esRef = useRef<EventSource | null>(null);
  const doneReceivedRef = useRef(false);

  const connect = useCallback((url: string) => {
    // Close any existing connection
    if (esRef.current) {
      esRef.current.close();
    }

    setState({ ...initialState, isLoading: true });
    doneReceivedRef.current = false;

    const es = new EventSource(url);
    esRef.current = es;

    const handleEvent = (eventType: string, rawData: string) => {
      try {
        const data = JSON.parse(rawData);

        // Mark done and close EventSource immediately — prevents the browser
        // from firing onerror when the server closes the SSE connection normally.
        if (eventType === 'done') {
          doneReceivedRef.current = true;
          esRef.current?.close();
          esRef.current = null;
        }

        setState(prev => {
          switch (eventType) {
            case 'summary':
              return {
                ...prev,
                summary: data.text ?? '',
                chapterName: data.chapter_name ?? '',
              };

            case 'mcqs':
              return {
                ...prev,
                questions: {
                  mcqs: data.mcqs ?? [],
                  short_answers: data.short_answers ?? [],
                  hot_question: data.hot_question ?? null,
                  exam_tip: data.exam_tip ?? '',
                },
              };

            case 'audio':
              return { ...prev, audioUrl: data.url };

            case 'video':
              return { ...prev, videoUrl: data.url };

            case 'examtip':
              return { ...prev, examTip: data.tip ?? '' };

            case 'error':
              return {
                ...prev,
                errors: [...prev.errors, { branch: data.branch, msg: data.msg }],
              };

            case 'done':
              return { ...prev, isLoading: false, isDone: true };

            default:
              return prev;
          }
        });
      } catch (e) {
        console.error('[useSSEStream] Failed to parse event data:', rawData, e);
      }
    };

    // Listen for named events
    const eventTypes = ['summary', 'mcqs', 'audio', 'video', 'examtip', 'error', 'done'];
    eventTypes.forEach(type => {
      es.addEventListener(type, (e: MessageEvent) => handleEvent(type, e.data));
    });

    es.onerror = () => {
      // Suppress the error if the stream closed normally after the 'done' event.
      // Browsers fire onerror when the server closes the SSE connection, even on success.
      if (doneReceivedRef.current) {
        es.close();
        return;
      }
      console.error('[useSSEStream] EventSource error');
      setState(prev => ({
        ...prev,
        isLoading: false,
        errors: [...prev.errors, { branch: 'connection', msg: 'Connection to server lost.' }],
      }));
      es.close();
    };
  }, []);

  const disconnect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setState(prev => ({ ...prev, isLoading: false }));
  }, []);

  const reset = useCallback(() => {
    disconnect();
    setState(initialState);
  }, [disconnect]);

  return { state, connect, disconnect, reset };
}
