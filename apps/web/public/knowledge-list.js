(() => {
  function apiUrl() {
    return window.NOTEBOOK_API_URL || "http://127.0.0.1:8000";
  }

  function getPanel(target) {
    return target?.closest?.(".knowledge-list-panel") ?? null;
  }

  function items(panel) {
    return Array.from(panel.querySelectorAll("[data-knowledge-item]"));
  }

  function checkboxes(panel) {
    return Array.from(panel.querySelectorAll("[data-knowledge-checkbox]"));
  }

  function selectedCheckboxes(panel) {
    return checkboxes(panel).filter((checkbox) => checkbox.checked);
  }

  function setError(panel, message) {
    const errorBox = panel.querySelector("[data-list-error]");
    if (!errorBox) return;
    errorBox.textContent = message || "";
    errorBox.hidden = !message;
  }

  function draftForm(target) {
    return target?.closest?.("[data-knowledge-draft-form]") ?? null;
  }

  function confirmForm(target) {
    return target?.closest?.("[data-confirm-ai-form]") ?? null;
  }

  function toggleMarkdownPreview(button) {
    const viewer = button.closest("[data-content-viewer]");
    if (!viewer) return;

    const rawPanel = viewer.querySelector("[data-markdown-raw-panel]");
    const previewPanel = viewer.querySelector("[data-markdown-preview-panel]");
    if (!rawPanel || !previewPanel) return;

    const showPreview = previewPanel.hidden;
    previewPanel.hidden = !showPreview;
    rawPanel.hidden = showPreview;
    button.setAttribute("aria-pressed", showPreview ? "true" : "false");
    button.textContent = showPreview ? "查看文本" : "预览 Markdown";
  }

  function ensureFormMessage(form, kind) {
    const attribute = `data-draft-${kind}`;
    let element = form.querySelector(`[${attribute}]`);
    if (element) return element;

    element = document.createElement("div");
    element.setAttribute(attribute, "");
    element.className = kind === "error" ? "form-error" : "form-status";
    element.hidden = true;
    element.setAttribute("role", kind === "error" ? "alert" : "status");
    form.querySelector(".form-actions")?.before(element);
    return element;
  }

  function setFormMessage(form, kind, message) {
    const element = ensureFormMessage(form, kind);
    element.textContent = message || "";
    element.hidden = !message;
  }

  function clearFormMessages(form) {
    setFormMessage(form, "error", "");
    setFormMessage(form, "status", "");
  }

  function formStorageKey(form) {
    return form.dataset.storageKey || "knowledge-draft-form:new";
  }

  function formSnapshot(form) {
    const formData = new FormData(form);
    return {
      title: String(formData.get("title") || ""),
      language: String(formData.get("language") || ""),
      topic: String(formData.get("topic") || ""),
      category_id: String(formData.get("category_id") || ""),
      raw_text: String(formData.get("raw_text") || ""),
    };
  }

  function saveDraftFormLocally(form) {
    try {
      window.sessionStorage.setItem(
        formStorageKey(form),
        JSON.stringify(formSnapshot(form)),
      );
    } catch {}
  }

  function restoreDraftForm(form) {
    let saved;
    try {
      saved = JSON.parse(window.sessionStorage.getItem(formStorageKey(form)) || "null");
    } catch {
      window.sessionStorage.removeItem(formStorageKey(form));
      return;
    }
    if (!saved) return;

    for (const [name, value] of Object.entries(saved)) {
      const field = form.elements.namedItem(name);
      if (!field || typeof field.value === "undefined") continue;
      field.value = value;
    }
  }

  async function parseJsonResponse(response) {
    if (response.ok) {
      return response.json();
    }

    let message = `请求失败（${response.status}）`;
    try {
      const payload = await response.json();
      if (payload.detail) message = payload.detail;
    } catch {}
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  async function requestJson(path, options) {
    const response = await fetch(apiUrl() + path, options);
    return parseJsonResponse(response);
  }

  async function submitDraftForm(form) {
    if (form.dataset.nativeSubmitting === "true") return;

    clearFormMessages(form);
    saveDraftFormLocally(form);
    const snapshot = formSnapshot(form);
    const rawText = snapshot.raw_text;
    if (!rawText.trim()) {
      setFormMessage(form, "error", "请输入需要保存的原始内容。");
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    const originalButtonText = button?.textContent || "";
    const isEditing = form.dataset.knowledgeEditing === "true";
    const blockId = form.dataset.blockId;
    const payload = {
      title: snapshot.title.trim() || undefined,
      topic: snapshot.topic.trim() || undefined,
      raw_text: rawText,
      language: snapshot.language.trim() || undefined,
      category_id: snapshot.category_id.trim() || null,
    };

    form.dataset.nativeSubmitting = "true";
    if (button) {
      button.disabled = true;
      button.textContent = isEditing ? "正在保存…" : "正在保存并整理…";
    }
    setFormMessage(
      form,
      "status",
      isEditing ? "正在保存新版本…" : "正在保存草稿…",
    );

    try {
      const block = isEditing && blockId
        ? await requestJson(`/knowledge-blocks/${encodeURIComponent(blockId)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          })
        : await requestJson("/knowledge-blocks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });

      window.sessionStorage.removeItem(formStorageKey(form));

      if (isEditing) {
        window.location.assign(`/knowledge/${block.id}`);
        return;
      }

      setFormMessage(form, "status", "草稿已保存，正在启动 AI 整理…");
      try {
        const job = await requestJson(`/knowledge-blocks/${encodeURIComponent(block.id)}/organize`, {
          method: "POST",
        });
        window.location.assign(
          `/knowledge/${block.id}?draftSaved=1&organizeStarted=1&jobId=${encodeURIComponent(job.id)}`,
        );
      } catch (error) {
        const suffix = error.status === 409 ? "organizeStarted=1" : "organizeError=1";
        window.location.assign(`/knowledge/${block.id}?draftSaved=1&${suffix}`);
      }
    } catch (error) {
      setFormMessage(
        form,
        "error",
        error.message || "保存失败，请确认知识库服务已启动。",
      );
      setFormMessage(form, "status", "");
      form.dataset.nativeSubmitting = "false";
      if (button) {
        button.disabled = false;
        button.textContent = originalButtonText;
      }
    }
  }

  async function submitConfirmForm(form) {
    if (form.dataset.nativeSubmitting === "true") return;

    clearFormMessages(form);
    const blockId = form.dataset.blockId;
    const formData = new FormData(form);
    const title = String(formData.get("title") || "").trim();
    const summary = String(formData.get("summary") || "").trim();
    const markdown = String(formData.get("markdown_content") || "").trim();
    const categoryId = String(formData.get("category_id") || "").trim();

    if (!blockId) {
      setFormMessage(form, "error", "缺少知识 ID，无法确认入库。");
      return;
    }
    if (!title || !markdown) {
      setFormMessage(form, "error", "标题和 Markdown 正文不能为空。");
      return;
    }

    const button = form.querySelector('button[type="submit"]');
    const originalButtonText = button?.textContent || "";
    form.dataset.nativeSubmitting = "true";
    if (button) {
      button.disabled = true;
      button.textContent = "正在入库…";
    }
    setFormMessage(form, "status", "正在确认并写入知识库…");

    try {
      await requestJson(`/knowledge-blocks/${encodeURIComponent(blockId)}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          summary: summary || null,
          markdown_content: markdown,
          category_id: categoryId || null,
        }),
      });
      window.location.assign(`/knowledge/${blockId}?confirmed=1`);
    } catch (error) {
      setFormMessage(form, "status", "");
      setFormMessage(
        form,
        "error",
        error.message || "确认失败，请稍后重试。",
      );
      form.dataset.nativeSubmitting = "false";
      if (button) {
        button.disabled = false;
        button.textContent = originalButtonText;
      }
    }
  }

  function setWorkflowMessage(panel, message, isError = false) {
    let element = panel.querySelector("[data-workflow-message]");
    if (!element) {
      element = document.createElement("div");
      element.setAttribute("data-workflow-message", "");
      element.setAttribute("role", isError ? "alert" : "status");
      panel.prepend(element);
    }
    element.className = isError ? "form-error" : "form-status";
    element.hidden = !message;
    element.textContent = message || "";
  }

  function finishOrganizeWatch(panel, status) {
    const url = new URL(window.location.href);
    url.searchParams.delete("organizeStarted");
    url.searchParams.delete("jobId");
    if (status === "succeeded") {
      url.searchParams.set("organizeDone", "1");
      window.location.replace(url.toString());
      return;
    }
    url.searchParams.set("organizeError", "1");
    window.location.replace(url.toString());
  }

  function watchOrganizeJob(panel) {
    const jobId = panel.dataset.organizeJobId;
    if (!jobId || panel.dataset.organizeWatching === "true") return;
    panel.dataset.organizeWatching = "true";

    let attempts = 0;
    async function poll() {
      attempts += 1;
      try {
        const job = await requestJson(`/jobs/${encodeURIComponent(jobId)}`, {
          method: "GET",
        });
        if (job.status === "succeeded" || job.status === "failed") {
          finishOrganizeWatch(panel, job.status);
          return;
        }
        setWorkflowMessage(
          panel,
          `AI 整理正在运行，已等待 ${attempts} 秒。完成后会自动显示确认表单。`,
        );
      } catch {
        setWorkflowMessage(
          panel,
          "暂时无法读取 AI 整理进度，仍会继续重试。",
          true,
        );
      }

      if (attempts < 180) {
        window.setTimeout(poll, 1000);
      } else {
        setWorkflowMessage(
          panel,
          "AI 整理仍在运行。可以稍后刷新页面查看确认结果。",
          true,
        );
      }
    }

    window.setTimeout(poll, 1000);
  }

  function updateCounts(panel) {
    const itemCount = items(panel).length;
    const selectedCount = selectedCheckboxes(panel).length;

    for (const item of items(panel)) {
      const checkbox = item.querySelector("[data-knowledge-checkbox]");
      item.dataset.selected = checkbox?.checked ? "true" : "false";
    }

    const countText = panel.querySelector("[data-list-count]");
    const selectionText = panel.querySelector("[data-selection-count]");
    const enterButton = panel.querySelector("[data-bulk-enter]");
    const allButton = panel.querySelector("[data-select-all]");
    const deleteSelectedButton = panel.querySelector("[data-delete-selected]");
    const restoreSelectedButton = panel.querySelector("[data-restore-selected]");
    const purgeSelectedButton = panel.querySelector("[data-purge-selected]");

    if (countText) countText.textContent = itemCount + " 条知识";
    if (selectionText) {
      selectionText.textContent = selectedCount
        ? "已选择 " + selectedCount + " 条"
        : "未选择知识";
    }
    if (deleteSelectedButton) deleteSelectedButton.disabled = selectedCount === 0;
    if (restoreSelectedButton) restoreSelectedButton.disabled = selectedCount === 0;
    if (purgeSelectedButton) purgeSelectedButton.disabled = selectedCount === 0;
    if (allButton) {
      allButton.textContent =
        itemCount > 0 && selectedCount === itemCount ? "取消全选" : "全选";
      allButton.disabled = itemCount === 0;
    }
    if (enterButton) enterButton.disabled = itemCount === 0;
  }

  function setBulkMode(panel, enabled) {
    panel.dataset.bulkMode = enabled ? "true" : "false";
    if (!enabled) {
      for (const checkbox of checkboxes(panel)) checkbox.checked = false;
      setError(panel, "");
    }
    updateCounts(panel);
  }

  async function deleteByIds(ids) {
    for (const id of ids) {
      const response = await fetch(
        apiUrl() + "/knowledge-blocks/" + encodeURIComponent(id),
        { method: "DELETE" },
      );
      if (!response.ok) {
        let message = "删除失败，请稍后重试。";
        try {
          const payload = await response.json();
          if (payload.detail) message = payload.detail;
        } catch {}
        throw new Error(message);
      }
    }
  }

  async function restoreByIds(ids) {
    for (const id of ids) {
      const response = await fetch(
        apiUrl() + "/knowledge-blocks/" + encodeURIComponent(id) + "/restore",
        { method: "POST" },
      );
      if (!response.ok) {
        let message = "恢复失败，请稍后重试。";
        try {
          const payload = await response.json();
          if (payload.detail) message = payload.detail;
        } catch {}
        throw new Error(message);
      }
    }
  }

  async function purgeByIds(ids) {
    for (const id of ids) {
      const response = await fetch(
        apiUrl() + "/knowledge-blocks/" + encodeURIComponent(id) + "/purge",
        { method: "DELETE" },
      );
      if (!response.ok) {
        let message = "彻底清除失败，请稍后重试。";
        try {
          const payload = await response.json();
          if (payload.detail) message = payload.detail;
        } catch {}
        throw new Error(message);
      }
    }
  }

  document.addEventListener("change", (event) => {
    const form = draftForm(event.target);
    if (form) {
      saveDraftFormLocally(form);
    }

    if (!event.target?.matches?.("[data-knowledge-checkbox]")) return;
    const panel = getPanel(event.target);
    if (panel) updateCounts(panel);
  });

  document.addEventListener("input", (event) => {
    const form = draftForm(event.target);
    if (form) {
      saveDraftFormLocally(form);
    }
  });

  document.addEventListener(
    "submit",
    (event) => {
      const form = draftForm(event.target) || confirmForm(event.target);
      if (!form) return;
      event.preventDefault();
      event.stopPropagation();
      if (form.matches("[data-confirm-ai-form]")) {
        submitConfirmForm(form);
      } else {
        submitDraftForm(form);
      }
    },
    true,
  );

  document.addEventListener("click", async (event) => {
    const target = event.target;
    const markdownPreviewButton = target.closest?.("[data-markdown-preview-toggle]");
    if (markdownPreviewButton) {
      event.preventDefault();
      toggleMarkdownPreview(markdownPreviewButton);
      return;
    }

    const panel = getPanel(target);
    if (!panel) return;

    if (target.closest("[data-bulk-enter]")) {
      setBulkMode(panel, true);
      return;
    }

    if (target.closest("[data-bulk-done]")) {
      setBulkMode(panel, false);
      return;
    }

    if (target.closest("[data-select-all]")) {
      const all = checkboxes(panel);
      const shouldSelect = selectedCheckboxes(panel).length !== all.length;
      for (const checkbox of all) checkbox.checked = shouldSelect;
      updateCounts(panel);
      return;
    }

    const deleteOneButton = target.closest("[data-delete-one]");
    if (deleteOneButton) {
      const item = deleteOneButton.closest("[data-knowledge-item]");
      if (!item) return;
      const title = item.dataset.title || "这条知识";
      if (!window.confirm("确认删除“" + title + "”吗？删除后默认列表中将不再显示。")) {
        return;
      }
      deleteOneButton.disabled = true;
      try {
        await deleteByIds([item.dataset.id]);
        item.remove();
        updateCounts(panel);
      } catch (error) {
        setError(panel, error.message || "删除失败，请稍后重试。");
        deleteOneButton.disabled = false;
      }
      return;
    }

    const restoreOneButton = target.closest("[data-restore-one]");
    if (restoreOneButton) {
      const item = restoreOneButton.closest("[data-knowledge-item]");
      if (!item) return;
      restoreOneButton.disabled = true;
      try {
        await restoreByIds([item.dataset.id]);
        item.remove();
        updateCounts(panel);
      } catch (error) {
        setError(panel, error.message || "恢复失败，请稍后重试。");
        restoreOneButton.disabled = false;
      }
      return;
    }

    const purgeOneButton = target.closest("[data-purge-one]");
    if (purgeOneButton) {
      const item = purgeOneButton.closest("[data-knowledge-item]");
      if (!item) return;
      const title = item.dataset.title || "这条知识";
      if (!window.confirm("确认彻底清除“" + title + "”吗？这个操作不能撤销。")) {
        return;
      }
      purgeOneButton.disabled = true;
      try {
        await purgeByIds([item.dataset.id]);
        item.remove();
        updateCounts(panel);
      } catch (error) {
        setError(panel, error.message || "彻底清除失败，请稍后重试。");
        purgeOneButton.disabled = false;
      }
      return;
    }

    const deleteSelectedButton = target.closest("[data-delete-selected]");
    if (deleteSelectedButton) {
      const selected = selectedCheckboxes(panel);
      if (selected.length === 0) return;
      const selectedItems = selected
        .map((checkbox) => checkbox.closest("[data-knowledge-item]"))
        .filter(Boolean);
      const names = selectedItems.map((item) => item.dataset.title || "未命名知识");
      const preview =
        names.length <= 3
          ? names.join("、")
          : names.slice(0, 3).join("、") + " 等 " + names.length + " 条";
      if (!window.confirm("确认删除已选的 " + selected.length + " 条知识吗？\n" + preview)) {
        return;
      }
      deleteSelectedButton.disabled = true;
      try {
        await deleteByIds(selectedItems.map((item) => item.dataset.id));
        for (const item of selectedItems) item.remove();
        setBulkMode(panel, false);
        updateCounts(panel);
      } catch (error) {
        setError(panel, error.message || "删除失败，请稍后重试。");
        deleteSelectedButton.disabled = false;
        updateCounts(panel);
      }
    }

    const restoreSelectedButton = target.closest("[data-restore-selected]");
    if (restoreSelectedButton) {
      const selected = selectedCheckboxes(panel);
      if (selected.length === 0) return;
      const selectedItems = selected
        .map((checkbox) => checkbox.closest("[data-knowledge-item]"))
        .filter(Boolean);
      restoreSelectedButton.disabled = true;
      try {
        await restoreByIds(selectedItems.map((item) => item.dataset.id));
        for (const item of selectedItems) item.remove();
        setBulkMode(panel, false);
        updateCounts(panel);
      } catch (error) {
        setError(panel, error.message || "恢复失败，请稍后重试。");
        restoreSelectedButton.disabled = false;
        updateCounts(panel);
      }
      return;
    }

    const purgeSelectedButton = target.closest("[data-purge-selected]");
    if (purgeSelectedButton) {
      const selected = selectedCheckboxes(panel);
      if (selected.length === 0) return;
      const selectedItems = selected
        .map((checkbox) => checkbox.closest("[data-knowledge-item]"))
        .filter(Boolean);
      const names = selectedItems.map((item) => item.dataset.title || "未命名知识");
      const preview =
        names.length <= 3
          ? names.join("、")
          : names.slice(0, 3).join("、") + " 等 " + names.length + " 条";
      if (!window.confirm("确认彻底清除已选的 " + selected.length + " 条知识吗？这个操作不能撤销。\\n" + preview)) {
        return;
      }
      purgeSelectedButton.disabled = true;
      try {
        await purgeByIds(selectedItems.map((item) => item.dataset.id));
        for (const item of selectedItems) item.remove();
        setBulkMode(panel, false);
        updateCounts(panel);
      } catch (error) {
        setError(panel, error.message || "彻底清除失败，请稍后重试。");
        purgeSelectedButton.disabled = false;
        updateCounts(panel);
      }
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    for (const panel of document.querySelectorAll(".knowledge-list-panel")) {
      updateCounts(panel);
    }
  });

  for (const form of document.querySelectorAll("[data-knowledge-draft-form]")) {
    restoreDraftForm(form);
  }

  for (const panel of document.querySelectorAll('[data-organize-watch="true"]')) {
    watchOrganizeJob(panel);
  }
})();
