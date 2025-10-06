/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React from "react"
import { X } from "lucide-react"

interface InfoModalProps {
  isOpen: boolean
  onClose: () => void
}

const InfoModal: React.FC<InfoModalProps> = ({ isOpen, onClose }) => {
  const DEFAULT_EXCHANGE_APP_API_URL = "http://127.0.0.1:8000"
  const EXCHANGE_APP_API_URL =
    import.meta.env.VITE_EXCHANGE_APP_API_URL || DEFAULT_EXCHANGE_APP_API_URL

  const [info, setInfo] = React.useState<{
    app: string
    service: string
    version: string
    build_date: string
    build_timestamp: string
    image: string
    dependencies: Record<string, string>
  } | null>(null)

  React.useEffect(() => {
    if (!isOpen) return
    ;(async () => {
      try {
        const res = await fetch(`${EXCHANGE_APP_API_URL}/build/info`)
        const data = await res.json()
        setInfo(data)
      } catch (e) {
        console.error("Failed to fetch build info:", e)
        setInfo(null)
      }
    })()
  }, [isOpen, EXCHANGE_APP_API_URL])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0" onClick={onClose} />

      <div className="absolute right-4 top-16 w-80 rounded-lg border border-modal-border bg-modal-background shadow-lg">
        <button
          onClick={onClose}
          className="absolute right-2 top-2 rounded-lg p-1 text-modal-text-secondary transition-colors hover:bg-modal-hover"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="space-y-4 p-4 pr-10">
          <div>
            <h3 className="mb-3 text-sm font-normal leading-5 tracking-wide text-modal-text">
              Build and Release Information
            </h3>
            <div className="space-y-2 text-sm text-modal-text-secondary">
              <div className="flex justify-between">
                <span>Release Version:</span>
                <span className="font-mono text-modal-accent">
                  {info?.version ?? "unknown"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Build Date:</span>
                <span className="font-mono">
                  {info?.build_date ?? "unknown"}
                </span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="mb-3 text-sm font-normal leading-5 tracking-wide text-modal-text">
              Dependencies:
            </h3>
            <div className="space-y-2 text-sm text-modal-text-secondary">
              {info?.dependencies &&
                Object.entries(info.dependencies).map(([name, ver]) => (
                  <div key={name} className="flex justify-between">
                    <span>{name}:</span>
                    <span className="font-mono text-modal-accent">{ver}</span>
                  </div>
                ))}
              {!info?.dependencies && (
                <div className="text-modal-text-secondary">
                  No dependency info
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default InfoModal
