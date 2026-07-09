export type KnowledgeBlockStatus =
  | "draft"
  | "organizing"
  | "pending_confirmation"
  | "indexing"
  | "searchable"
  | "index_failed"
  | "archived"
  | "deleted";

export type KnowledgeBlockSummary = {
  id: string;
  title: string;
  summary: string | null;
  status: KnowledgeBlockStatus;
  source_type: string;
  language: string | null;
  category_id: string | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
};

export type KnowledgeVersion = {
  id: string;
  version_number: number;
  version_type: string;
  topic_instruction: string | null;
  raw_text: string | null;
  markdown_content: string | null;
  structured_metadata: Record<string, unknown>;
  created_by: string;
  content_hash: string;
  created_at: string;
};

export type Attachment = {
  id: string;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  sha256: string;
  width: number | null;
  height: number | null;
  extracted_text: string | null;
  processing_status: string;
  created_at: string;
};

export type IngestionJob = {
  id: string;
  knowledge_block_id: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  attempt_count: number;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type KnowledgeChunk = {
  id: string;
  knowledge_version_id: string;
  chunk_index: number;
  heading_path: string[];
  content: string;
  token_count: number;
  char_start: number | null;
  char_end: number | null;
  content_hash: string;
  is_active: boolean;
  created_at: string;
};

export type KnowledgeBlockDetail = KnowledgeBlockSummary & {
  category_id: string | null;
  current_version_id: string | null;
  source_uri: string | null;
  confirmed_at: string | null;
  archived_at: string | null;
  deleted_at: string | null;
  versions: KnowledgeVersion[];
  attachments: Attachment[];
  ingestion_jobs: IngestionJob[];
  chunks: KnowledgeChunk[];
};

export type KnowledgeBlockList = {
  items: KnowledgeBlockSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type SearchHit = {
  knowledge_block_id: string;
  knowledge_chunk_id: string;
  title: string;
  summary: string | null;
  category_id: string | null;
  heading_path: string[];
  snippet: string;
  score: number;
};

export type SearchResponse = {
  query: string;
  total: number;
  limit: number;
  items: SearchHit[];
};

export type KnowledgeDraftInput = {
  topic?: string;
  title?: string;
  raw_text: string;
  language?: string;
  category_id?: string | null;
};

export type KnowledgeBlockUpdateInput = {
  title?: string;
  topic?: string | null;
  raw_text?: string;
  markdown_content?: string;
  summary?: string | null;
  language?: string | null;
  category_id?: string | null;
};

export type KnowledgeConfirmInput = {
  title: string;
  summary?: string | null;
  markdown_content: string;
  category_id?: string | null;
};

export type Category = {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  is_system: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type CategoryInput = {
  name: string;
  description?: string | null;
  color?: string | null;
};

export type OrganizerProvider = "local" | "minimax" | "deepseek";

export type LocalOrganizerProviderSettings = {
  label: string;
  description: string;
};

export type ModelOrganizerProviderSettings = {
  label: string;
  base_url: string;
  model: string;
  max_tokens: number;
  api_key_configured: boolean;
};

export type DeepSeekOrganizerProviderSettings = ModelOrganizerProviderSettings & {
  thinking_enabled: boolean;
};

export type AIOrganizerSettings = {
  organizer_provider: OrganizerProvider;
  providers: {
    local: LocalOrganizerProviderSettings;
    minimax: ModelOrganizerProviderSettings;
    deepseek: DeepSeekOrganizerProviderSettings;
  };
};

export type ModelOrganizerProviderUpdate = {
  api_key?: string | null;
  base_url?: string | null;
  model?: string | null;
  max_tokens?: number | null;
};

export type DeepSeekOrganizerProviderUpdate = ModelOrganizerProviderUpdate & {
  thinking_enabled?: boolean | null;
};

export type AIOrganizerSettingsUpdate = {
  organizer_provider: OrganizerProvider;
  minimax?: ModelOrganizerProviderUpdate;
  deepseek?: DeepSeekOrganizerProviderUpdate;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class KnowledgeApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the HTTP status fallback when the response is not JSON.
    }
    throw new KnowledgeApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export async function listKnowledgeBlocks(input?: {
  category_id?: string | null;
  uncategorized?: boolean;
  statuses?: KnowledgeBlockStatus[];
}): Promise<KnowledgeBlockList> {
  const params = new URLSearchParams({ limit: "100", offset: "0" });
  if (input?.category_id) {
    params.set("category_id", input.category_id);
  }
  if (input?.uncategorized) {
    params.set("uncategorized", "true");
  }
  for (const status of input?.statuses ?? []) {
    params.append("status", status);
  }
  const response = await fetch(`${API_URL}/knowledge-blocks?${params}`, {
    cache: "no-store",
  });
  return parseResponse<KnowledgeBlockList>(response);
}

export async function getKnowledgeBlock(id: string): Promise<KnowledgeBlockDetail> {
  const response = await fetch(`${API_URL}/knowledge-blocks/${id}`, {
    cache: "no-store",
  });
  return parseResponse<KnowledgeBlockDetail>(response);
}

export async function createKnowledgeDraft(
  input: KnowledgeDraftInput,
): Promise<KnowledgeBlockDetail> {
  const response = await fetch(`${API_URL}/knowledge-blocks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<KnowledgeBlockDetail>(response);
}

export async function updateKnowledgeDraft(
  id: string,
  input: KnowledgeDraftInput,
): Promise<KnowledgeBlockDetail> {
  return updateKnowledgeBlock(id, input);
}

export async function updateKnowledgeBlock(
  id: string,
  input: KnowledgeBlockUpdateInput,
): Promise<KnowledgeBlockDetail> {
  const response = await fetch(`${API_URL}/knowledge-blocks/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<KnowledgeBlockDetail>(response);
}

export async function confirmKnowledgeBlock(
  id: string,
  input: KnowledgeConfirmInput,
): Promise<KnowledgeBlockDetail> {
  const response = await fetch(`${API_URL}/knowledge-blocks/${id}/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<KnowledgeBlockDetail>(response);
}

export async function deleteKnowledgeBlock(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/knowledge-blocks/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await parseResponse<never>(response);
  }
}

export async function listDeletedKnowledgeBlocks(): Promise<KnowledgeBlockList> {
  const response = await fetch(`${API_URL}/knowledge-blocks/deleted?limit=100&offset=0`, {
    cache: "no-store",
  });
  return parseResponse<KnowledgeBlockList>(response);
}

export async function restoreKnowledgeBlock(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/knowledge-blocks/${id}/restore`, {
    method: "POST",
  });
  if (!response.ok) {
    await parseResponse<never>(response);
  }
}

export async function purgeKnowledgeBlock(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/knowledge-blocks/${id}/purge`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await parseResponse<never>(response);
  }
}

export async function listCategories(): Promise<Category[]> {
  const response = await fetch(`${API_URL}/categories`, {
    cache: "no-store",
  });
  return parseResponse<Category[]>(response);
}

export async function searchKnowledge(input: {
  query: string;
  limit?: number;
  category_id?: string | null;
}): Promise<SearchResponse> {
  const response = await fetch(`${API_URL}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: input.query,
      limit: input.limit ?? 20,
      category_id: input.category_id ?? null,
    }),
    cache: "no-store",
  });
  return parseResponse<SearchResponse>(response);
}

export async function createCategory(input: CategoryInput): Promise<Category> {
  const response = await fetch(`${API_URL}/categories`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<Category>(response);
}

export async function updateCategory(
  id: string,
  input: CategoryInput,
): Promise<Category> {
  const response = await fetch(`${API_URL}/categories/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<Category>(response);
}

export async function deleteCategory(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/categories/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await parseResponse<never>(response);
  }
}

export async function uploadAttachment(
  blockId: string,
  file: File,
): Promise<Attachment> {
  const form = new FormData();
  form.set("file", file);
  const response = await fetch(
    `${API_URL}/knowledge-blocks/${blockId}/attachments`,
    {
      method: "POST",
      body: form,
    },
  );
  return parseResponse<Attachment>(response);
}

export async function organizeKnowledgeBlock(
  blockId: string,
): Promise<IngestionJob> {
  const response = await fetch(
    `${API_URL}/knowledge-blocks/${blockId}/organize`,
    { method: "POST" },
  );
  return parseResponse<IngestionJob>(response);
}

export async function getIngestionJob(jobId: string): Promise<IngestionJob> {
  const response = await fetch(`${API_URL}/jobs/${jobId}`, {
    cache: "no-store",
  });
  return parseResponse<IngestionJob>(response);
}

export async function getAIOrganizerSettings(): Promise<AIOrganizerSettings> {
  const response = await fetch(`${API_URL}/settings/ai-organizer`, {
    cache: "no-store",
  });
  return parseResponse<AIOrganizerSettings>(response);
}

export async function updateAIOrganizerSettings(
  input: AIOrganizerSettingsUpdate,
): Promise<AIOrganizerSettings> {
  const response = await fetch(`${API_URL}/settings/ai-organizer`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  return parseResponse<AIOrganizerSettings>(response);
}
