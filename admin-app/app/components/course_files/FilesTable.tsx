import React, { useMemo, useState } from "react";
import type { ColumnsType } from "antd/es/table";
import {
  Table,
  Tag,
  Space,
  Button,
  Tooltip,
  DatePicker,
  Select,
  Typography,
  Popconfirm,
  Flex,
} from "antd";
import {
  CloudUploadOutlined,
  DeleteOutlined,
  DeleteTwoTone,
  LinkOutlined,
} from "@ant-design/icons";
import dayjs, { Dayjs } from "dayjs";

const { RangePicker } = DatePicker;
const { Text } = Typography;

interface Document {
  _id: string;
  name: string;
  url: string;
  version_id: string;
  date_str: string; // "YYYY-MM-DD"
  time_str: string; // "HH:mm:ss"
  in_vector_store: string; // "yes" or "no"
  is_root_blob: string;    // "yes" or "no"
}

interface FileTableProps {
  files: Document[];
  collectionName: string;
  onFileDeleted: (
    id: string,
    collection: string,
    file: string,
    version_id: string,
    is_root_blob: string
  ) => void;
  onFileMoved: (
    id: string,
    collection: string,
    file: string,
    version_id: string
  ) => void;
  onBlobDeleted: (
    id: string,
    collection: string,
    file: string,
    version_id: string,
    is_root_blob: string
  ) => void;
}

const DOC_EXTS = [".pdf", ".docx", ".pptx", ".txt"];
const VIDEO_EXTS = [".mp4", ".mov", ".mkv", ".webm", ".avi"];

const getExt = (name: string) => {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
};
const isDoc = (name: string) => DOC_EXTS.includes(getExt(name));
const isVideo = (name: string) => VIDEO_EXTS.includes(getExt(name));

const FilesTable: React.FC<FileTableProps> = ({
  files,
  collectionName,
  onFileDeleted,
  onFileMoved,
  onBlobDeleted,
}) => {
  // toolbar filters
  const [vecFilter, setVecFilter] = useState<"yes" | "no" | "">("");
  const [rootFilter, setRootFilter] = useState<"yes" | "no" | "">("");
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  const filtered = useMemo(() => {
    return (files || []).filter((d) => {
      const vecOk = !vecFilter || d.in_vector_store === vecFilter;
      const rootOk = !rootFilter || d.is_root_blob === rootFilter;

      if (!range || (!range[0] && !range[1])) return vecOk && rootOk;

      const docDay = dayjs(d.date_str, "YYYY-MM-DD");
      const startOk = !range[0] || docDay.isSame(range[0], "day") || docDay.isAfter(range[0], "day");
      const endOk = !range[1] || docDay.isSame(range[1], "day") || docDay.isBefore(range[1], "day");
      return vecOk && rootOk && startOk && endOk;
    });
  }, [files, vecFilter, rootFilter, range]);

  const columns: ColumnsType<Document> = [
    {
      title: "File Name",
      dataIndex: "name",
      key: "name",
      ellipsis: true,
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (_, record) => (
        <Space size="small" wrap>
          <Tooltip title="Open/download">
            <a href={record.url} download={record.name} target="_blank" rel="noreferrer">
              <LinkOutlined /> {record.name}
            </a>
          </Tooltip>
          {isDoc(record.name) && <Tag color="cyan">Document</Tag>}
          {isVideo(record.name) && <Tag color="purple">Video</Tag>}
        </Space>
      ),
    },
    {
      title: "Vectorized",
      dataIndex: "in_vector_store",
      key: "vector",
      width: 140,
      filters: [
        { text: "Yes", value: "yes" },
        { text: "No", value: "no" },
      ],
      onFilter: (v, rec) => rec.in_vector_store === v,
      render: (v: string) =>
        v === "yes" ? <Tag color="green">Searchable</Tag> : <Tag>Stored only</Tag>,
    },
    {
      title: "Root File",
      dataIndex: "is_root_blob",
      key: "root",
      width: 120,
      filters: [
        { text: "Yes", value: "yes" },
        { text: "No", value: "no" },
      ],
      onFilter: (v, rec) => rec.is_root_blob === v,
      render: (v: string) => (v === "yes" ? <Tag color="blue">Root</Tag> : <Tag>Derived</Tag>),
    },
    {
      title: "Date",
      dataIndex: "date_str",
      key: "date",
      width: 140,
      sorter: (a, b) =>
        dayjs(a.date_str, "YYYY-MM-DD").valueOf() - dayjs(b.date_str, "YYYY-MM-DD").valueOf(),
      render: (v: string) => <Text>{v}</Text>,
    },
    {
      title: "Time",
      dataIndex: "time_str",
      key: "time",
      width: 120,
      sorter: (a, b) => a.time_str.localeCompare(b.time_str),
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    {
      title: "Actions",
      key: "actions",
      width: 340,
      render: (_, d) => {
        const canDelete = d.in_vector_store === "yes" || d.is_root_blob === "yes";
        const canDeleteFromStorage = d.in_vector_store === "no" && d.is_root_blob === "no";
        const canMove = d.in_vector_store === "no"; // your original logic shows move in both root/non-root when not vectorized

        return (
          <Space size="small" wrap>
            {canDelete && (
              <Popconfirm
                title="Delete record"
                description="This removes the record (blob if it's root)."
                okText="Delete"
                okButtonProps={{ danger: true }}
                onConfirm={() =>
                  onFileDeleted(d._id, collectionName, d.name, d.version_id, d.is_root_blob)
                }
              >
                <Button danger icon={<DeleteOutlined />}>
                  Delete
                </Button>
              </Popconfirm>
            )}

            {canDeleteFromStorage && (
              <Popconfirm
                title="Delete from storage"
                description="This deletes the blob from file storage."
                okText="Delete"
                okButtonProps={{ danger: true }}
                onConfirm={() =>
                  onBlobDeleted(d._id, collectionName, d.name, d.version_id, d.is_root_blob)
                }
              >
                <Button danger type="dashed" icon={<DeleteTwoTone twoToneColor="#ff4d4f" />}>
                  Delete From File Storage
                </Button>
              </Popconfirm>
            )}

            {canMove && (
              <Tooltip title="Add this file’s content to your vector store">
                <Button
                  type="primary"
                  icon={<CloudUploadOutlined />}
                  onClick={() => onFileMoved(d._id, collectionName, d.name, d.version_id)}
                >
                  Move to vector store
                </Button>
              </Tooltip>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {/* Filter toolbar */}
      <Flex gap={12} align="center" wrap style={{ marginBottom: 12 }}>
        <Space size="small" align="center">
          <Text strong>Vectorized</Text>
          <Select
            size="middle"
            style={{ width: 140 }}
            value={vecFilter}
            onChange={(v) => setVecFilter(v)}
            options={[
              { label: "All", value: "" },
              { label: "Yes", value: "yes" },
              { label: "No", value: "no" },
            ]}
          />
        </Space>

        <Space size="small" align="center">
          <Text strong>Root</Text>
          <Select
            size="middle"
            style={{ width: 120 }}
            value={rootFilter}
            onChange={(v) => setRootFilter(v)}
            options={[
              { label: "All", value: "" },
              { label: "Yes", value: "yes" },
              { label: "No", value: "no" },
            ]}
          />
        </Space>

        <Space size="small" align="center">
          <Text strong>Date</Text>
          <RangePicker
            value={range as any}
            onChange={(vals) => setRange(vals as any)}
            allowEmpty={[true, true]}
            style={{ width: 280 }}
          />
          {(vecFilter || rootFilter || (range && (range[0] || range[1]))) && (
            <Button onClick={() => { setVecFilter(""); setRootFilter(""); setRange(null); }}>
              Clear filters
            </Button>
          )}
        </Space>

        <Text type="secondary" style={{ marginLeft: "auto" }}>
          Showing {filtered.length} of {files.length}
        </Text>
      </Flex>

      <Table<Document>
        rowKey="_id"
        columns={columns}
        dataSource={filtered}
        size="middle"
        bordered
        sticky
        pagination={{ pageSize: 10, showSizeChanger: true }}
        scroll={{ x: 1000 }}
      />
    </div>
  );
};

export default FilesTable;
