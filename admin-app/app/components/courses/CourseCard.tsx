"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { RiDeleteBin6Line } from "react-icons/ri";
import { IoFolderOutline } from "react-icons/io5";
import { FaShare } from "react-icons/fa";
import { IoMdPeople } from "react-icons/io";

import { Card, Typography, Space, Button, Tooltip, Popconfirm } from "antd";

const { Text } = Typography;

interface CourseProps {
  courseName: string;
  userType: string;
  onCourseDeleted: (courseName: string) => void;
  onCourseShare: (courseName: string) => void;
  onManageAccess: (courseName: string) => void;
}

const CourseCard: React.FC<CourseProps> = ({
  courseName,
  userType,
  onCourseDeleted,
  onCourseShare,
  onManageAccess,
}) => {
  const router = useRouter();
  const [totalFiles, setTotalFiles] = useState<number>(0);

  useEffect(() => {
    fetch(`http://localhost:5000/api/${courseName}/totalFiles`)
      .then((response) => {
        if (!response.ok) throw new Error("Failed to fetch collections");
        return response.json();
      })
      .then((noOfFiles: number) => setTotalFiles(noOfFiles))
      .catch((error) => console.error("Error fetching collections:", error));
  }, [courseName]);

  const goToCourse = () => router.push(`/knowledgebase_management/${courseName}`);

  return (
    <Card
      hoverable
      onClick={goToCourse}
      style={{ width: "100%" }}
      bodyStyle={{ padding: 16 }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        {/* Left: folder icon + course info */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
          <div
            style={{
              width: 40,
              height: 40,
              background: "#2C3463",
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: "0 0 auto",
            }}
          >
            <IoFolderOutline color="#fff" size={20} />
          </div>
          <div style={{ minWidth: 0 }}>
            <Text strong style={{ color: "#2C3463" }} ellipsis>
              {courseName}
            </Text>
            <div>
              <Text type="secondary">{totalFiles} Files</Text>
            </div>
          </div>
        </div>

        {/* Right: actions (only for root_user) */}
        {userType === "root_user" && (
          <Space>
            <Tooltip title="Manage Access">
              <Button
                type="text"
                shape="circle"
                onClick={(e) => {
                  e.stopPropagation();
                  onManageAccess(courseName);
                }}
                icon={<IoMdPeople size={18} color="#2C3463" />}
              />
            </Tooltip>

            <Tooltip title="Share">
              <Button
                type="text"
                shape="circle"
                onClick={(e) => {
                  e.stopPropagation();
                  onCourseShare(courseName);
                }}
                icon={<FaShare size={16} color="#2C3463" />}
              />
            </Tooltip>

            <Tooltip title="Delete">
              <Popconfirm
                placement="left"
                title="Delete course"
                description="Are you sure you want to delete this course?"
                onConfirm={(e) => {
                  // prevent card navigation
                  e?.stopPropagation?.();
                  onCourseDeleted(courseName);
                }}
                onCancel={(e) => e?.stopPropagation?.()}
                okText="Yes"
                cancelText="Cancel"
                // Inline sizing fix for the popconfirm buttons if you need it:
                okButtonProps={{
                  size: "small",
                  style: { fontSize: 12, lineHeight: 1.2, padding: "4px 12px" },
                }}
                cancelButtonProps={{
                  size: "small",
                  style: { fontSize: 12, lineHeight: 1.2, padding: "4px 12px" },
                }}
              >
                <Button
                  type="text"
                  shape="circle"
                  danger
                  onClick={(e) => e.stopPropagation()}
                  icon={<RiDeleteBin6Line size={16} />}
                />
              </Popconfirm>
            </Tooltip>
          </Space>
        )}
      </div>
    </Card>
  );
};

export default CourseCard;
