import { useCallback, useState, useRef } from 'react'
import { toast } from 'sonner'
import { Upload } from 'lucide-react'
import { Card } from '@/components/ui/card'

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md']
const MAX_SIZE = 10 * 1024 * 1024

interface FileUploaderProps {
  onFileSelect: (file: File) => void
  disabled?: boolean
}

export function FileUploader({ onFileSelect, disabled }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const validateFile = useCallback((file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported format: ${ext}. Supported: PDF, DOCX, TXT, MD`
    }
    if (file.size > MAX_SIZE) {
      return `File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB. Max: 10MB`
    }
    return null
  }, [])

  const handleFile = useCallback((file: File) => {
    const error = validateFile(file)
    if (error) {
      toast.error(error)
      return
    }
    onFileSelect(file)
  }, [onFileSelect, validateFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (disabled) return
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [disabled, handleFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }, [disabled])

  return (
    <Card
      className={`cursor-pointer border-4 border-dashed p-12 text-center transition-colors ${
        isDragging ? 'border-black bg-[#c4b5fd]' : 'border-gray-400 bg-white'
      } ${disabled ? 'cursor-not-allowed opacity-50' : 'hover:border-black hover:bg-[#f0ecff]'}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setIsDragging(false)}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <Upload className="mx-auto mb-4 h-12 w-12 text-gray-500" />
      <p className="mb-2 text-lg font-bold">
        Drag & drop your resume here
      </p>
      <p className="text-sm text-gray-600">
        or click to select a file
      </p>
      <p className="mt-2 text-xs text-gray-400">
        Supported: PDF, DOCX, TXT, MD (max 10MB)
      </p>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.docx,.txt,.md"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
          e.target.value = ''
        }}
      />
    </Card>
  )
}
