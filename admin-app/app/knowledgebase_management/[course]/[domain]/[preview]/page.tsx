"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams, useParams, useRouter } from "next/navigation";
import { Typography, Button, Spin, Space } from "antd";
import { MessageOutlined } from "@ant-design/icons";

const { Title, Paragraph, Text } = Typography;

type PreviewKind = "text" | "pdf" | "video" | "office" | "other";

interface PreviewResponse {
  name: string;
  kind: PreviewKind;
  content?: string;
  url?: string;
  id?: string; // Optional ID from backend
}

const PreviewPage: React.FC = () => {
  const searchParams = useSearchParams();
  const { course, domain } = useParams<{ course: string; domain: string }>();
  const router = useRouter();

  // 1. Get 'name' and 'id' from the URL parameters
  // The 'id' here is passed from your FilesTable (it is the vi_mongo_id)
  const name = searchParams.get("name") || "";
  const passedId = searchParams.get("id"); 

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!name || !course || !domain) return;

    setLoading(true);
    setError(null);

    fetch(
      `/api/preview/${encodeURIComponent(
        course as string
      )}/${encodeURIComponent(domain as string)}?name=${encodeURIComponent(
        name
      )}`
    )
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json: PreviewResponse) => {
        setPreview(json);
      })
      .catch((err) => {
        console.error("Preview error:", err);
        setError(err.message || String(err));
      })
      .finally(() => setLoading(false));
  }, [course, domain, name]);

  if (!name) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={3}>No file selected</Title>
        <Button onClick={() => router.back()}>Back</Button>
      </div>
    );
  }


  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          marginBottom: 8,
          marginTop: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>
            {preview?.name || name}
          </Title>
          <Text type="secondary">
            {String(course)} / {String(domain)}
          </Text>
        </div>

        {/* Button Area */}
        <Space>
          <Button onClick={() => router.back()}>Back</Button>
        </Space>
      </div>

      {/* Loading & error */}
      {loading && (
        <div style={{ marginTop: 16 }}>
          <Spin />
        </div>
      )}

      {error && (
        <div style={{ marginTop: 16 }}>
          <Paragraph>
            <Text type="danger">Failed to load preview: {error}</Text>
          </Paragraph>
        </div>
      )}

      {/* Main content */}
      {!loading && !error && preview && (
        <div style={{ marginTop: 16 }}>
          {/* TEXT PREVIEW */}
          {preview.kind === "text" && (
            <>
              <Paragraph type="secondary">
                 {preview.name.endsWith('.csv') ? "CSV Preview" : "Text Preview"}
              </Paragraph>
              <div
                style={{
                  background: "#f5f5f5",
                  borderRadius: 8,
                  padding: 16,
                  maxHeight: "70vh",
                  overflow: "auto",
                  border: "1px solid #e5e5e5",
                }}
              >
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontFamily:
                      'SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                    fontSize: 13,
                  }}
                >
                  {preview.content}
                </pre>
              </div>
            </>
          )}

          {/* PDF PREVIEW */}
          {preview.kind === "pdf" && preview.url && (
            <>
              <Paragraph type="secondary">PDF preview</Paragraph>
              <div
                style={{
                  borderRadius: 8,
                  overflow: "hidden",
                  border: "1px solid #e5e5e5",
                }}
              >
                <iframe
                  src={preview.url}
                  title={preview.name}
                  style={{
                    width: "100%",
                    height: "80vh",
                    border: "none",
                  }}
                />
              </div>
            </>
          )}

           {/* OFFICE (.docx) PREVIEW */}
           {preview.kind === "office" && preview.url && (
            <>
              <Paragraph type="secondary">Document Preview</Paragraph>
              <div style={{ borderRadius: 8, overflow: "hidden", border: "1px solid #e5e5e5" }}>
                <iframe
                  src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(preview.url)}`}
                  title={preview.name}
                  style={{ width: "100%", height: "80vh", border: "none" }}
                />
              </div>
              <div style={{ marginTop: 8, textAlign: "right" }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                    Powered by Microsoft Office Viewer
                </Text>
              </div>
            </>
          )}

          {/* VIDEO PREVIEW */}
          {preview.kind === "video" && preview.url && (
            <>
              <Paragraph type="secondary">Video preview</Paragraph>
              <video
                controls
                src={preview.url}
                style={{ width: "100%", maxHeight: "70vh", borderRadius: 8 }}
              />
            </>
          )}

          {/* OTHER TYPES */}
          {preview.kind === "other" && preview.url && (
            <>
              <Paragraph>
                Inline preview for this file type is not implemented yet. You
                can still open or download the file:
              </Paragraph>
              <Button type="primary">
                <a href={preview.url} target="_blank" rel="noreferrer">
                  Open in new tab
                </a>
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default PreviewPage;