'use client'

import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Camera, X, Check, AlertCircle, User } from 'lucide-react'

interface PhotoUploadProps {
  onUpload: (file: File) => Promise<void>
  onSkip?: () => void
  isLoading?: boolean
}

export default function PhotoUpload({ onUpload, onSkip, isLoading = false }: PhotoUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    // Check file type
    if (!file.type.startsWith('image/')) {
      return 'Please upload an image file (JPG, PNG)'
    }
    
    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      return 'Image must be smaller than 10MB'
    }
    
    return null
  }

  const handleFile = useCallback(async (file: File) => {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setError(null)
    
    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
      setPreview(e.target?.result as string)
    }
    reader.readAsDataURL(file)

    // Upload
    try {
      await onUpload(file)
    } catch (err) {
      setError('Failed to upload image. Please try again.')
      setPreview(null)
    }
  }, [onUpload])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFile(file)
    }
  }, [handleFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFile(file)
    }
  }, [handleFile])

  const clearPreview = () => {
    setPreview(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="w-full max-w-md mx-auto p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <h1 className="text-2xl font-semibold text-[#1d1d1f] mb-2">
          Create Your Avatar
        </h1>
        <p className="text-[#86868b]">
          Upload a photo to see how clothes fit on your body
        </p>
      </motion.div>

      {/* Upload Area */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
      >
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`
            relative w-full aspect-[3/4] rounded-3xl cursor-pointer
            border-2 border-dashed transition-all duration-300
            ${isDragging 
              ? 'border-[#007AFF] bg-blue-50/50' 
              : 'border-gray-200 hover:border-gray-300 bg-gray-50/50'
            }
            ${preview ? 'border-transparent' : ''}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleInputChange}
            className="hidden"
          />

          <AnimatePresence mode="wait">
            {preview ? (
              <motion.div
                key="preview"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 rounded-3xl overflow-hidden"
              >
                <img
                  src={preview}
                  alt="Preview"
                  className="w-full h-full object-cover"
                />
                
                {/* Loading overlay */}
                {isLoading && (
                  <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center">
                    <div className="w-12 h-12 border-3 border-white border-t-transparent rounded-full animate-spin mb-4" />
                    <p className="text-white font-medium">Creating your avatar...</p>
                    <p className="text-white/70 text-sm mt-1">This takes about 30 seconds</p>
                  </div>
                )}

                {/* Clear button */}
                {!isLoading && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      clearPreview()
                    }}
                    className="absolute top-4 right-4 w-10 h-10 rounded-full bg-black/50 backdrop-blur
                               flex items-center justify-center text-white hover:bg-black/70 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </motion.div>
            ) : (
              <motion.div
                key="upload"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-8"
              >
                <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mb-6">
                  <User className="w-10 h-10 text-gray-400" />
                </div>
                
                <div className="w-16 h-16 rounded-full bg-[#007AFF]/10 flex items-center justify-center mb-4">
                  <Upload className="w-8 h-8 text-[#007AFF]" />
                </div>
                
                <p className="text-[#1d1d1f] font-medium mb-1">
                  Drag & drop your photo
                </p>
                <p className="text-[#86868b] text-sm mb-4">
                  or click to browse
                </p>
                
                <div className="flex items-center gap-2 text-xs text-[#86868b]">
                  <Camera className="w-4 h-4" />
                  <span>Front-facing, full body works best</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-4 p-4 rounded-2xl bg-red-50 flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-600">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tips */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="mt-6 glass-panel p-4"
      >
        <h3 className="text-sm font-medium text-[#1d1d1f] mb-3">
          Photo tips for best results
        </h3>
        <ul className="space-y-2">
          {[
            'Stand straight, facing the camera',
            'Wear fitted clothing (not baggy)',
            'Good lighting, plain background',
            'Include your full body, head to toe',
          ].map((tip, i) => (
            <li key={i} className="flex items-center gap-2 text-xs text-[#86868b]">
              <Check className="w-3.5 h-3.5 text-[#34C759]" />
              {tip}
            </li>
          ))}
        </ul>
      </motion.div>

      {/* Skip Option */}
      {onSkip && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          onClick={onSkip}
          className="w-full mt-4 py-3 text-sm text-[#86868b] hover:text-[#1d1d1f] transition-colors"
        >
          Skip for now — use a demo avatar
        </motion.button>
      )}

      {/* Privacy Note */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-center text-[10px] text-[#86868b] mt-6"
      >
        🔒 Your photo is processed securely and deleted after avatar creation.
        <br />
        We never store or share your images. <a href="#" className="underline">Privacy Policy</a>
      </motion.p>
    </div>
  )
}
