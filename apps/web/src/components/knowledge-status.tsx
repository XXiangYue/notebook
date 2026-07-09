const statusLabels: Record<string, string> = {
  draft: "草稿",
  organizing: "整理中",
  pending_confirmation: "待确认",
  indexing: "索引中",
  searchable: "已确认",
  index_failed: "索引失败",
  archived: "已归档",
  deleted: "已删除",
};

export function KnowledgeStatus({ status }: { status: string }) {
  return (
    <span className={`status status-${status}`}>
      {statusLabels[status] ?? status}
    </span>
  );
}
