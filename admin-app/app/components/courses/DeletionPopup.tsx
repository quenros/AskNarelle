import React, { useState } from 'react';
import { Modal, Button, Typography, Alert, Spin, message } from 'antd';

interface DeletionPopupProps {
  onClose: () => void;
  onCourseDeleted: () => void;
  courseName: string;
  username: string; 
}

const DeletionPopup: React.FC<DeletionPopupProps> = ({ onClose, onCourseDeleted, courseName }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleDelete = async () => {
    try {
      setIsLoading(true);
      const resp = await fetch('http://localhost:5000/api/deletecourse', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collectionName: courseName }),
      });

      if (resp.status === 201) {
        message.success('Course deleted successfully');
        onCourseDeleted();
        onClose();
      } else {
        const data = await resp.json().catch(() => ({}));
        const err = typeof data?.message === 'string' ? data.message : 'Failed to delete course';
        message.error(err);
      }
    } catch (e: any) {
      message.error(e?.message ?? 'Error deleting course');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      title="Delete course?"
      open={true}
      onCancel={isLoading ? undefined : onClose}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={isLoading}>
          No
        </Button>,
        <Button key="ok" type="primary" danger onClick={handleDelete} loading={isLoading}>
          Yes, delete
        </Button>,
      ]}
      maskClosable={!isLoading}
      closable={!isLoading}
      destroyOnClose
    >
      <Typography.Paragraph strong>
        Are you sure you want to delete <Typography.Text code>{courseName}</Typography.Text>?
      </Typography.Paragraph>

      <Alert
        type="error"
        showIcon
        message="Warning"
        description="Deleting this folder will delete all the content inside."
        style={{ marginBottom: 12 }}
      />

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Spin />
          <Typography.Text>Deleting…</Typography.Text>
        </div>
      )}
    </Modal>
  );
};

export default DeletionPopup;
