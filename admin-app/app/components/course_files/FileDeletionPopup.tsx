import React, { useState } from "react";
import { Modal, Button, Typography, Space, Tag, Alert, Spin, message } from "antd";
import { ExclamationCircleOutlined } from "@ant-design/icons";

interface FileDeletionPopupProps {
  fileName: string;
  collectionName: string;
  domainName: string;
  id: string; // File Storage ID
  version_id: string;
  is_root_blob: string; // "yes" | "no"
  username: string;
  vi_mongo_id?: string; 
  onFileDeleted: () => void;
  onClose: () => void;
}


const FileDeletionPopup: React.FC<FileDeletionPopupProps> = ({
  fileName,
  collectionName,
  domainName,
  id,
  version_id,
  is_root_blob,
  username,
  vi_mongo_id,
  onFileDeleted,
  onClose,
}) => {
  const [open] = useState(true);
  const [loading, setLoading] = useState(false);
  const isRoot = is_root_blob === "yes";

  const doJSON = async (resp: Response) => {
    try {
      return await resp.json();
    } catch {
      return {};
    }
  };

  const handleDelete = async () => {
    setLoading(true);
    let embedOk = false;

    try {
      // ---------------------------------------------------------
      // 1) Handle Video Indexer Deletion
      // ---------------------------------------------------------
      // Only attempt if we actually have a Video Indexer ID passed to us
      if (vi_mongo_id) {
        try {
          const vResp = await fetch(`/api/vi/delete_video`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: vi_mongo_id }), // Use the VI Mongo ID
          });
          
          if (!vResp.ok) {
            console.warn("Failed to delete from Video Indexer, proceeding to blob delete.");
          }
        } catch (vErr) {
          console.error("Error contacting Video Indexer delete API", vErr);
        }
      }

      // ---------------------------------------------------------
      // 2) Delete Embeddings
      // ---------------------------------------------------------
      const eResp = await fetch(`/api/${collectionName}/deleteembeddings`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ _id: id, fileName }),
      });
      embedOk = eResp.ok || eResp.status === 201;

      // ---------------------------------------------------------
      // 3) Delete Document (Blob + generic Record)
      // ---------------------------------------------------------
      const dResp = await fetch(
        `/api/${collectionName}/${domainName}/deletedocument`,
        {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            _id: id,
            fileName,
            versionId: version_id,
            isRootBlob: is_root_blob,
            username,
            action: "File Deletion",
          }),
        }
      );

      const dJson = await doJSON(dResp);
      if (dResp.ok || dResp.status === 201) {
        message.success("File deleted successfully");
        onFileDeleted();
        onClose();
      } else {
        const errText =
          typeof dJson?.error === "string"
            ? dJson.error
            : `${dResp.status} ${dResp.statusText}`;
        message.error(errText || "Failed to delete file");
      }
    } catch (err: any) {
      message.error(err?.message ?? "Error deleting file");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title={
        <Space align="center">
          <ExclamationCircleOutlined style={{ color: "#faad14" }} />
          <span>Delete file?</span>
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
          key="delete"
          danger
          type="primary"
          onClick={handleDelete}
          loading={loading}
        >
          Delete
        </Button>,
      ]}
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Space wrap>
          <Typography.Text strong>File:</Typography.Text>
          <Typography.Text code>{fileName}</Typography.Text>
          {isRoot ? <Tag color="blue">Root</Tag> : <Tag>Derived</Tag>}
          {version_id ? <Tag>ver: {version_id}</Tag> : null}
        </Space>

        {isRoot ? (
          <Alert
            type="warning"
            showIcon
            message="Deleting the root blob"
            description="This will remove the base file and may affect any derived versions if they exist."
          />
        ) : (
          <Alert
            type="info"
            showIcon
            message="Delete file"
            description="This removes the record, and if applicable, the blob from file storage."
          />
        )}

        {loading && (
          <Space align="center">
            <Spin />
            <Typography.Text>Deleting…</Typography.Text>
          </Space>
        )}
      </Space>
    </Modal>
  );
};

export default FileDeletionPopup;