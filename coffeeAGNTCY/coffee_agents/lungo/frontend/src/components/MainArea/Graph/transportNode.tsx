/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React from "react"
import { Handle, Position } from "@xyflow/react"
import { useThemeIcon } from "@/hooks/useThemeIcon"
import githubIcon from "@/assets/Github.png"
import githubIconLight from "@/assets/Github_lightmode.png"

interface TransportNodeData {
  label: string
  active?: boolean
  githubLink?: string
  compact?: boolean
}

interface TransportNodeProps {
  data: TransportNodeData
}

const TransportNode: React.FC<TransportNodeProps> = ({ data }) => {
  const githubIconSrc = useThemeIcon({
    light: githubIconLight,
    dark: githubIcon,
  })

  const activeClasses = data.active
    ? "bg-node-background-active outline outline-2 outline-accent-border shadow-[var(--shadow-default)_0px_6px_8px]"
    : "bg-node-background"

  return (
    <div
      className={` ${activeClasses} relative flex h-[120px] w-[120px] flex-col items-center justify-center rounded-full p-4 text-center text-gray-50 hover:bg-node-background-hover hover:shadow-[var(--shadow-default)_0px_6px_8px] hover:outline hover:outline-2 hover:outline-accent-border`}
    >
      <div className="mb-2 flex h-auto w-auto items-center justify-center whitespace-nowrap text-center font-inter text-xs font-normal leading-4 tracking-normal text-node-text-primary opacity-100">
        {data.label}
      </div>

      {data.githubLink && (
        <a
          href={data.githubLink}
          target="_blank"
          rel="noopener noreferrer"
          className="no-underline"
        >
          <div
            className="flex h-6 w-6 cursor-pointer items-center justify-center rounded-lg border border-solid p-1 opacity-100 shadow-sm transition-opacity duration-200 ease-in-out"
            style={{
              backgroundColor: "var(--custom-node-background)",
              borderColor: "var(--custom-node-border)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = "0.8"
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = "1"
            }}
          >
            <img src={githubIconSrc} alt="GitHub" className="h-4 w-4" />
          </div>
        </a>
      )}

      <Handle
        type="target"
        id="top"
        position={Position.Top}
        className="h-[0.1px] w-[0.1px] border border-gray-600 bg-node-data-background"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom_left"
        className="h-[0.1px] w-[0.1px] border border-gray-600 bg-node-data-background"
        style={{
          left: "25%",
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom_center"
        className="h-[0.1px] w-[0.1px] border border-gray-600 bg-node-data-background"
        style={{
          left: "50%",
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom_right"
        className="h-[0.1px] w-[0.1px] border border-gray-600 bg-node-data-background"
        style={{
          left: "75%",
        }}
      />
    </div>
  )
}

export default TransportNode
