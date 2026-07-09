"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  AIOrganizerSettings,
  KnowledgeApiError,
  OrganizerProvider,
  updateAIOrganizerSettings,
} from "@/lib/knowledge-api";

type AIOrganizerSettingsFormProps = {
  settings: AIOrganizerSettings;
};

const providerNames: Record<OrganizerProvider, string> = {
  local: "Local",
  minimax: "MiniMax",
  deepseek: "DeepSeek V4 Flash",
};

export function AIOrganizerSettingsForm({
  settings,
}: AIOrganizerSettingsFormProps) {
  const router = useRouter();
  const [provider, setProvider] = useState<OrganizerProvider>(
    settings.organizer_provider,
  );
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    try {
      const updated = await updateAIOrganizerSettings({
        organizer_provider: provider,
        minimax: {
          api_key: optionalText(form.get("minimax_api_key")),
          base_url: requiredText(form.get("minimax_base_url")),
          model: requiredText(form.get("minimax_model")),
          max_tokens: requiredNumber(form.get("minimax_max_tokens")),
        },
        deepseek: {
          api_key: optionalText(form.get("deepseek_api_key")),
          base_url: requiredText(form.get("deepseek_base_url")),
          model: requiredText(form.get("deepseek_model")),
          max_tokens: requiredNumber(form.get("deepseek_max_tokens")),
          thinking_enabled: form.get("deepseek_thinking_enabled") === "on",
        },
      });
      setProvider(updated.organizer_provider);
      setMessage("AI 整理设置已保存，新的整理任务会使用当前配置。");
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof KnowledgeApiError ? caught.message : "保存设置失败。",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <section className="settings-panel">
        <div className="settings-section-heading">
          <p className="eyebrow">Organizer mode</p>
          <h2>选择 AI 整理模式</h2>
        </div>
        <label className="settings-provider-select">
          当前模式
          <select
            name="organizer_provider"
            onChange={(event) =>
              setProvider(event.currentTarget.value as OrganizerProvider)
            }
            value={provider}
          >
            <option value="local">Local</option>
            <option value="minimax">MiniMax</option>
            <option value="deepseek">DeepSeek V4 Flash</option>
          </select>
        </label>
        <div className="provider-grid">
          {(["local", "minimax", "deepseek"] as OrganizerProvider[]).map(
            (item) => (
              <button
                className="provider-card"
                data-active={provider === item}
                key={item}
                onClick={() => setProvider(item)}
                type="button"
              >
                <strong>{providerNames[item]}</strong>
                <span>{providerDescription(settings, item)}</span>
              </button>
            ),
          )}
        </div>
      </section>

      <section className="settings-panel" data-active={provider === "local"}>
        <div className="settings-section-heading">
          <p className="eyebrow">Local</p>
          <h2>本地整理</h2>
          <p>{settings.providers.local.description}</p>
        </div>
      </section>

      <section className="settings-panel" data-active={provider === "minimax"}>
        <div className="settings-section-heading">
          <p className="eyebrow">MiniMax</p>
          <h2>MiniMax 配置</h2>
          <p>使用 Anthropic 兼容接口，保留图片附件的多模态整理能力。</p>
        </div>
        <div className="settings-fields">
          <label>
            API Key
            <input
              autoComplete="off"
              name="minimax_api_key"
              placeholder={secretPlaceholder(
                settings.providers.minimax.api_key_configured,
              )}
              type="password"
            />
          </label>
          <label>
            Base URL
            <input
              defaultValue={settings.providers.minimax.base_url}
              name="minimax_base_url"
              required
            />
          </label>
          <label>
            模型
            <input
              defaultValue={settings.providers.minimax.model}
              name="minimax_model"
              required
            />
          </label>
          <label>
            Max Tokens
            <input
              defaultValue={settings.providers.minimax.max_tokens}
              min={1}
              name="minimax_max_tokens"
              required
              type="number"
            />
          </label>
        </div>
      </section>

      <section className="settings-panel" data-active={provider === "deepseek"}>
        <div className="settings-section-heading">
          <p className="eyebrow">DeepSeek</p>
          <h2>DeepSeek V4 Flash 配置</h2>
          <p>使用 DeepSeek 官方 OpenAI 兼容 Chat Completions 接口。</p>
        </div>
        <div className="settings-fields">
          <label>
            API Key
            <input
              autoComplete="off"
              name="deepseek_api_key"
              placeholder={secretPlaceholder(
                settings.providers.deepseek.api_key_configured,
              )}
              type="password"
            />
          </label>
          <label>
            Base URL
            <input
              defaultValue={settings.providers.deepseek.base_url}
              name="deepseek_base_url"
              required
            />
          </label>
          <label>
            模型
            <input
              defaultValue={settings.providers.deepseek.model}
              name="deepseek_model"
              required
            />
          </label>
          <label>
            Max Tokens
            <input
              defaultValue={settings.providers.deepseek.max_tokens}
              min={1}
              name="deepseek_max_tokens"
              required
              type="number"
            />
          </label>
          <label className="settings-checkbox">
            <input
              defaultChecked={settings.providers.deepseek.thinking_enabled}
              name="deepseek_thinking_enabled"
              type="checkbox"
            />
            启用 thinking 模式
          </label>
        </div>
      </section>

      {error ? (
        <div className="form-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <div className="form-status">{message}</div> : null}
      <div className="form-actions">
        <p>API Key 只保存在本机运行时配置文件中；留空提交表示沿用已配置的密钥。</p>
        <button className="button" disabled={submitting} type="submit">
          {submitting ? "保存中…" : "保存设置"}
        </button>
      </div>
    </form>
  );
}

function optionalText(value: FormDataEntryValue | null): string | null {
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

function requiredText(value: FormDataEntryValue | null): string {
  return String(value ?? "").trim();
}

function requiredNumber(value: FormDataEntryValue | null): number {
  return Number(String(value ?? "").trim());
}

function secretPlaceholder(configured: boolean): string {
  return configured ? "已配置，留空表示不修改" : "请输入 API Key";
}

function providerDescription(
  settings: AIOrganizerSettings,
  provider: OrganizerProvider,
): string {
  if (provider === "local") {
    return "离线开发适配器，不调用外部模型。";
  }
  const providerSettings =
    provider === "minimax" ? settings.providers.minimax : settings.providers.deepseek;
  return `${providerSettings.model} · ${
    providerSettings.api_key_configured ? "已配置密钥" : "未配置密钥"
  }`;
}
