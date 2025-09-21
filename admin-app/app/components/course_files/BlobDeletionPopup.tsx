import React, { useState } from "react";
import { Modal, Button, Typography, Space, Tag, Alert, Spin, message } from "antd";
import { ExclamationCircleOutlined } from "@ant-design/icons";

interface BlobDeletionPopupProps {
  fileName: string;
  collectionName: string;
  domainName: string;
  id: string;
  version_id: string;
  is_root_blob: string; // "yes" | "no"
  username: string;
  onBlobDeleted: () => void;
  onClose: () => void;
}

const BlobDeletionPopup: React.FC<BlobDeletionPopupProps> = ({
  fileName,
  collectionName,
  domainName,
  id,
  version_id,
  is_root_blob,
  username,
  onBlobDeleted,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [open] = useState(true);

  const handleBlobDelete = async () => {
    try {
      setLoading(true);
      const resp = await fetch(
        `http://localhost:5000/api/${collectionName}/${domainName}/deletedocument`,
        {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            _id: id,
            fileName,
            versionId: version_id,
            isRootBlob: is_root_blob,
            username,
            action: "Blob Deletion",
          }),
        }
      );

      const maybeJson = await resp
        .json()
        .catch(() => ({ error: `${resp.status} ${resp.statusText}` }));

      if (resp.ok || resp.status === 201) {
        message.success("File deleted successfully");
        onBlobDeleted();
        onClose();
      } else {
        const errMsg =
          typeof maybeJson?.error === "string"
            ? maybeJson.error
            : "Failed to delete file";
        message.error(errMsg);
      }
    } catch (e: any) {
      message.error(e?.message ?? "Error deleting file");
    } finally {
      setLoading(false);
    }
  };

  const isRoot = is_root_blob === "yes";

  return (
    <Modal
      open={open}
      title={
        <Space align="center">
          <ExclamationCircleOutlined style={{ color: "#faad14" }} />
          <span>Delete {isRoot ? "root" : "blob"} file?</span>
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
          onClick={handleBlobDelete}
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
          {version_id ? <Tag color="default">ver: {version_id}</Tag> : null}
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
            message="Delete from storage"
            description="This removes this specific blob from file storage."
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

export default BlobDeletionPopup;
