import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Upload,
  Button,
  Typography,
  Space,
  Steps,
  Switch,
  Slider,
  message,
} from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import { InboxOutlined } from "@ant-design/icons";

interface PopupProps {
  onClose: () => void;
  onFileCreated: () => void;
  collectionName: string;
  domainName: string;
  username: string;
}

const { Dragger } = Upload;
const { Text } = Typography;

const DOC_EXTS = [".pdf", ".docx", ".pptx", ".txt"];
const VIDEO_EXTS = [".mp4", ".mov", ".mkv", ".webm", ".avi"];
const ACCEPT = [
  ...DOC_EXTS,
  ...VIDEO_EXTS,
].join(",");

const isDoc = (name?: string) =>
  !!name && DOC_EXTS.some((ext) => name.toLowerCase().endsWith(ext));
const isVideo = (name?: string) =>
  !!name && VIDEO_EXTS.some((ext) => name.toLowerCase().endsWith(ext));

const DocumentPopup: React.FC<PopupProps> = ({
  onClose,
  onFileCreated,
  collectionName,
  domainName,
  username,
}) => {
  const [open] = useState(true);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [loading, setLoading] = useState(false);

  // optional “advanced” chunking
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(100);

  // progress stepper
  // 0=Select, 1=Upload to Blob, 2=Vector store, 3=Database
  const [step, setStep] = useState(0);

  const docFiles = useMemo(
    () => fileList.filter((f) => isDoc(f.name)),
    [fileList]
  );
  const videoFiles = useMemo(
    () => fileList.filter((f) => isVideo(f.name)),
    [fileList]
  );
  const hasDocs = docFiles.length > 0;
  const hasVideos = videoFiles.length > 0;

  const beforeUpload = () => false; // prevent auto-upload; we upload manually
  const onRemove = (f: UploadFile) => {
    setFileList((prev) => prev.filter((x) => x.uid !== f.uid));
    return true;
  };

  const doFetch = async (url: string, init: RequestInit) => {
    const resp = await fetch(url, init);
    if (!resp.ok) {
      let err = await resp.text().catch(() => "");
      try {
        const j = JSON.parse(err);
        err = j?.message || j?.error || err;
      } catch {}
      throw new Error(err || `${resp.status} ${resp.statusText}`);
    }
    return resp;
  };

  const buildFormData = () => {
    const fd = new FormData();
    fileList.forEach((f) => {
      if (f.originFileObj) fd.append("files", f.originFileObj);
    });
    return fd;
  };

  const handleSubmit = async () => {
    if (fileList.length === 0) {
      message.warning("Please select at least one file.");
      return;
    }
    setLoading(true);
    setStep(1);

    try {
      // 1) Upload to Blob
      const formData = buildFormData();
      await doFetch(
        `http://localhost:5000/api/${collectionName}/${domainName}/${username}/createblob`,
        { method: "PUT", body: formData }
      );

      // 2) Only vectorize *documents* (skip videos)
      if (hasDocs) {
        setStep(2);
        console.log(collectionName)
        console.log(chunkSize)
        console.log(overlap)
        await doFetch("http://localhost:5000/vectorstore", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            containername: collectionName,
            chunksize: chunkSize,
            overlap: overlap,
          }),
        });
      }

      // 3) Create DB records (for both docs & videos)
      setStep(3);
      await doFetch(
        `http://localhost:5000/api/${collectionName}/${domainName}/${username}/createdocument`,
        { method: "PUT", body: buildFormData() }
      );

      message.success("Files uploaded successfully");
      onFileCreated();
      onClose();
    } catch (err: any) {
      message.error(err?.message || "Upload failed");
    } finally {
      setLoading(false);
      setStep(0);
    }
  };

  return (
    <Modal
      title="Add files"
      open={open}
      onCancel={loading ? undefined : onClose}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={loading}>
          Cancel
        </Button>,
        <Button
          key="submit"
          type="primary"
          onClick={handleSubmit}
          loading={loading}
        >
          Upload
        </Button>,
      ]}
      maskClosable={!loading}
      closable={!loading}
      destroyOnClose
    >
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Steps
          current={step}
          size="small"
          items={[
            { title: "Select" },
            { title: "Blob" },
            { title: "Vector" },
            { title: "Database" },
          ]}
        />

        <Dragger
          multiple
          fileList={fileList}
          onChange={({ fileList }) => setFileList(fileList)}
          beforeUpload={beforeUpload}
          onRemove={onRemove}
          accept={ACCEPT}
          disabled={loading}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            Click or drag files to this area to upload
          </p>
          <p className="ant-upload-hint">
            Allowed: PDF, DOCX, PPTX, TXT, and videos (MP4, MOV, MKV, WEBM,
            AVI). Videos are stored but not vectorized.
          </p>
        </Dragger>

        <Space direction="vertical" style={{ width: "100%" }}>
          <Text type="secondary">
            {hasDocs
              ? `Will vectorize ${docFiles.length} document(s).`
              : "No documents selected for vectorization."}
          </Text>
          {hasVideos && (
            <Text type="secondary">
              {videoFiles.length} video file(s) will be uploaded to storage and
              listed, but skipped for embeddings.
            </Text>
          )}
        </Space>

        <Space align="center" style={{ width: "100%" }}>
          <Switch
            checked={showAdvanced}
            onChange={setShowAdvanced}
            disabled={loading}
          />
          <Text>Advanced chunk settings</Text>
        </Space>

        {showAdvanced && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <div>
              <Text strong>Chunk size</Text>
              <Slider
                min={500}
                max={2000}
                step={50}
                value={chunkSize}
                onChange={(v) => setChunkSize(v as number)}
                tooltip={{ open: true }}
              />
            </div>
            <div>
              <Text strong>Overlap</Text>
              <Slider
                min={0}
                max={500}
                step={10}
                value={overlap}
                onChange={(v) => setOverlap(v as number)}
                tooltip={{ open: true }}
              />
            </div>
          </Space>
        )}
      </Space>
    </Modal>
  );
};

export default DocumentPopup;
