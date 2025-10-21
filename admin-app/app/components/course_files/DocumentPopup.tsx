import React, { useMemo, useState } from "react";
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
const ACCEPT = [...DOC_EXTS, ...VIDEO_EXTS].join(",");

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

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(100);

  // 0=Select, 1=Blob, 2=Vector, 3=Database / VI
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

  const beforeUpload = () => false;
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

  // Build FormData with docs only (videos handled via VI API)
  const buildDocsFormData = () => {
    const fd = new FormData();
    docFiles.forEach((f) => {
      if (f.originFileObj) fd.append("files", f.originFileObj);
    });
    return fd;
  };

  const fileToBase64 = (file: File) =>
    new Promise<string>((resolve, reject) => {
      const r = new FileReader();
      r.onloadend = () => (r.result ? resolve(r.result as string) : reject(new Error("Failed to read file")));
      r.onerror = reject;
      r.readAsDataURL(file);
    });

  const uploadVideosViaVI = async () => {
    if (!hasVideos) return;

    const videoPayload = await Promise.all(
      videoFiles.map(async (vf) => {
        const f = vf.originFileObj as File;
        const base64 = await fileToBase64(f);
        return {
          video_name: vf.name,
          base64_encoded_video: base64,
          video_description: "",
        };
      })
    );

    setStep(3);
    await doFetch("http://localhost:5000/vi/videos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        courseCode: collectionName,
        video: videoPayload,
      }),
    });
  };

  const handleSubmit = async () => {
    if (fileList.length === 0) {
      message.warning("Please select at least one file.");
      return;
    }
    setLoading(true);
    setStep(1);

    try {
      // 1) DOCS → Blob
      if (hasDocs) {
        const formData = buildDocsFormData();
        await doFetch(
          `http://localhost:5000/api/${collectionName}/${domainName}/${username}/createblob`,
          { method: "PUT", body: formData }
        );
      }

      // 2) DOCS → Vector
      if (hasDocs) {
        setStep(2);
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

      // 3A) DOCS → DB
      if (hasDocs) {
        setStep(3);
        await doFetch(
          `http://localhost:5000/api/${collectionName}/${domainName}/${username}/createdocument`,
          { method: "PUT", body: buildDocsFormData() }
        );
      }

      // 3B) VIDEOS → VI API
      if (hasVideos) {
        await uploadVideosViaVI();
      }

      message.success("Upload complete");
      onFileCreated();
      onClose();
    } catch (err: any) {
      console.error(err);
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
            { title: "Database / VI" },
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
            Allowed: PDF, DOCX, PPTX, TXT (docs go to Blob → Vector → DB) and
            videos (MP4, MOV, MKV, WEBM, AVI) which go to Video Indexer API.
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
              {videoFiles.length} video file(s) will be sent to the Video
              Indexer API (not stored in Blob or vectorized here).
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
