// Language Evolution Types

export interface LanguageMetrics {
  word_count: number;
  sentiment: number;
  topics: string[];
  vocabulary_new_words: string[];
  style: {
    question_ratio: number;
    avg_sentence_length: number;
    first_person_ratio: number;
    exclamation_ratio: number;
    sentence_count: number;
  };
}

export interface LanguageContentItem {
  id: string;
  type: 'read' | 'comment' | 'share';
  timestamp: string;
  darwin_content: string;
  original_content?: string;
  source_post_id?: string;
  source_post_title?: string;
  metrics: LanguageMetrics;
  metadata?: Record<string, unknown>;
}

export interface DailyMetrics {
  date: string;
  content_count: number;
  total_words: number;
  new_vocabulary_count: number;
  avg_sentiment: number;
  topic_counts: Record<string, number>;
  style_markers: {
    question_ratio: number;
    avg_sentence_length: number;
    first_person_ratio: number;
  };
  cumulative_vocabulary_size: number;
}

export interface HistoryItem {
  date: string;
  content_count: number;
  total_words: number;
  new_vocabulary_count: number;
  avg_sentiment: number;
  cumulative_vocabulary_size: number;
  top_topics: [string, number][];
}

export interface VocabularyGrowthItem {
  date: string;
  vocabulary_size: number;
  new_words: number;
}

export interface LanguageEvolutionSummary {
  total_content_count: number;
  total_word_count: number;
  vocabulary_size: number;
  first_content_date?: string;
  today: {
    content_count: number;
    words_written: number;
    new_vocabulary: number;
    avg_sentiment: number;
  };
  recent_sentiment: number;
  top_topics: [string, number][];
  sample_vocabulary: string[];
}

export interface ContentArchiveResponse {
  items: LanguageContentItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface TopicTrends {
  [topic: string]: { date: string; count: number }[];
}
