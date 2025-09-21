import React, { useState } from "react";
import {
  Modal,
  Button,
  Typography,
  Space,
  Slider,
  Switch,
  Alert,
  Spin,
  message,
  Tag,
} from "antd";
import { CloudUploadOutlined } from "@ant-design/icons";

interface FileMovementPopupProps {
  fileName: string;
  collectionName: string;
  domainName: string;
  id: string;
  version_id: string;
  username: string;
  onFileMoved: () => void;
  onClose: () => void;
}

const FileMovementPopup: React.FC<FileMovementPopupProps> = ({
  fileName,
  collectionName,
  domainName,
  id,
  version_id,
  username,
  onFileMoved,
  onClose,
}) => {
  const [open] = useState(true);
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [chunkSize, setChunkSize] = useState(1000);
  const [overlap, setOverlap] = useState(100);

  const doJSON = async (resp: Response) => {
    try {
      return await resp.json();
    } catch {
      return {};
    }
  };

  const handleMove = async () => {
    try {
      setLoading(true);

      // 1) Move to vector store (embed + upsert)
      const moveResp = await fetch(`http://localhost:5000/movetovectorstore`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          containername: collectionName,
          domainname: domainName,
          versionid: version_id,
          filename: fileName,
          chunksize: chunkSize,
          overlap: overlap,
        }),
      });

      if (!(moveResp.ok || moveResp.status === 201)) {
        const j = await doJSON(moveResp);
        const err =
          (typeof j?.error === "string" && j.error) ||
          `${moveResp.status} ${moveResp.statusText}`;
        throw new Error(err || "Failed to move file to vector store");
      }

      // 2) Update DB flag / activity
      const updResp = await fetch(`http://localhost:5000/updatemovement`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          _id: id,
          collectionName,
          domainName,
          fileName,
          versionId: version_id,
          username,
        }),
      });

      if (!(updResp.ok || updResp.status === 201)) {
        const j = await doJSON(updResp);
        const err =
          (typeof j?.error === "string" && j.error) ||
          `${updResp.status} ${updResp.statusText}`;
        throw new Error(err || "Failed to update movement status");
      }

      message.success("Moved to vector store");
      onFileMoved();
      onClose();
    } catch (e: any) {
      message.error(e?.message ?? "Move failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title={
        <Space align="center">
          <CloudUploadOutlined />
          <span>Move to vector store?</span>
        </Space>
      }
      onCancel={loading ? undefined : onClose}
      maskClosable={!loading}
      closable={!loading}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={onClose} disabled={loading}>
          Cancel
        </Button>,
        <Button
          key="move"
          type="primary"
          icon={<CloudUploadOutlined />}
          loading={loading}
          onClick={handleMove}
        >
          Move
        </Button>,
      ]}
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Space wrap>
          <Typography.Text strong>File:</Typography.Text>
          <Typography.Text code>{fileName}</Typography.Text>
          {version_id ? <Tag>ver: {version_id}</Tag> : null}
        </Space>

        <Alert
          type="info"
          showIcon
          message="What happens next?"
          description="The file will be embedded and added to your vector index so it becomes searchable. Large files may take longer."
        />

        <Space align="center">
          <Switch
            checked={showAdvanced}
            onChange={setShowAdvanced}
            disabled={loading}
          />
          <Typography.Text>Advanced chunk settings</Typography.Text>
        </Space>

        {showAdvanced && (
          <Space direction="vertical" style={{ width: "100%" }}>
            <div>
              <Typography.Text strong>Chunk size</Typography.Text>
              <Slider
                min={500}
                max={2000}
                step={50}
                value={chunkSize}
                onChange={(v) => setChunkSize(v as number)}
                disabled={loading}
                tooltip={{ open: true }}
              />
            </div>
            <div>
              <Typography.Text strong>Overlap</Typography.Text>
              <Slider
                min={0}
                max={500}
                step={10}
                value={overlap}
                onChange={(v) => setOverlap(v as number)}
                disabled={loading}
                tooltip={{ open: true }}
              />
            </div>
          </Space>
        )}

        {loading && (
          <Space align="center">
            <Spin />
            <Typography.Text>Moving file to vector store…</Typography.Text>
          </Space>
        )}
      </Space>
    </Modal>
  );
};

export default FileMovementPopup;
