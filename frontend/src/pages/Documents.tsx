import { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Search, FileText, MoreVertical, CheckCircle, Clock, AlertCircle, Loader2, Download, Trash2 } from 'lucide-react';
import {
  Button,
  Input,
  Card,
  CardContent,
  Badge,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui';
import { CardSkeleton } from '@/components/ui/TypingIndicator';
import apiClient, { getApiErrorMessage } from '@/lib/api';
import type { DocumentStatus, DocumentType } from '@/types/api';

// Framer Motion variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { x: -20, opacity: 0 },
  visible: {
    x: 0,
    opacity: 1,
    transition: { type: 'spring' as const, stiffness: 100, damping: 15 },
  },
};

// Backend returns snake_case, so define the actual response type
interface BackendDocument {
  id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  document_type: DocumentType;
  status: DocumentStatus;
  page_count?: number;
  created_at: string;
}

export function Documents() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const vendorIdFromUrl = searchParams.get('vendor_id');
  const [searchQuery, setSearchQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<BackendDocument | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const { data: documentsResponse, isLoading } = useQuery({
    queryKey: ['documents', searchQuery],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      params.append('limit', '50');

      const response = await apiClient.get(`/documents?${params}`);
      return response.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);

      // If arriving from a vendor detail page, associate the document with that vendor
      const url = vendorIdFromUrl
        ? `/documents?vendor_id=${encodeURIComponent(vendorIdFromUrl)}`
        : '/documents';

      // Document upload triggers text extraction and chunking which can be slow for large files
      const response = await apiClient.post(url, formData, { timeout: 120000 });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      // Also invalidate vendor-documents so the vendor detail page refreshes
      if (vendorIdFromUrl) {
        queryClient.invalidateQueries({ queryKey: ['vendor-documents', vendorIdFromUrl] });
      }
      setUploadError(null);
    },
    onError: (error) => {
      setUploadError(getApiErrorMessage(error));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setShowDeleteModal(false);
      setSelectedDocument(null);
    },
  });

  const documents: BackendDocument[] = documentsResponse?.data || [];

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    // Validate by both MIME type and file extension for better security
    const validExtensions = ['.pdf', '.docx'];
    const validMimeTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const validFiles = files.filter((f) => {
      const ext = f.name.toLowerCase().slice(f.name.lastIndexOf('.'));
      return validMimeTypes.includes(f.type) && validExtensions.includes(ext);
    });

    validFiles.forEach((file) => {
      uploadMutation.mutate(file);
    });
  }, [uploadMutation]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach((file) => {
      uploadMutation.mutate(file);
    });
    e.target.value = '';
  }, [uploadMutation]);

  const handleDownload = async (doc: BackendDocument) => {
    setOpenMenuId(null);
    try {
      const response = await apiClient.get(`/documents/${doc.id}/download`, {
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response.data], { type: doc.mime_type });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = doc.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      setUploadError(getApiErrorMessage(error));
    }
  };

  const openDeleteModal = (doc: BackendDocument) => {
    setSelectedDocument(doc);
    setShowDeleteModal(true);
    setOpenMenuId(null);
  };

  const handleDelete = () => {
    if (!selectedDocument) return;
    deleteMutation.mutate(selectedDocument.id);
  };

  const getStatusIcon = (status: DocumentStatus) => {
    switch (status) {
      case 'analyzed':
      case 'processed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getDocTypeLabel = (docType: DocumentType) => {
    const labels: Record<DocumentType, string> = {
      soc2: 'SOC 2',
      sig_lite: 'SIG Lite',
      sig_core: 'SIG Core',
      hecvat: 'HECVAT',
      iso27001: 'ISO 27001',
      pentest: 'Pentest',
      questionnaire: 'Questionnaire',
      other: 'Other',
    };
    return labels[docType] || docType;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6 pb-8"
    >
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-5xl font-bold tracking-tighter text-white neon-text mb-2">
            DOCUMENT<span className="text-primary">VAULT</span>
          </h1>
          {vendorIdFromUrl && (
            <div className="mb-2 px-3 py-1.5 rounded-md bg-primary/10 border border-primary/30 text-sm text-primary font-mono inline-flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              UPLOADING FOR VENDOR — documents will be linked automatically
            </div>
          )}
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <motion.span
                className="w-2 h-2 rounded-full bg-green-500"
                animate={{ scale: [1, 1.2, 1], opacity: [1, 0.7, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              AI ANALYSIS READY
            </span>
            <span className="text-white/10">|</span>
            <span className="font-mono text-primary/80">
              {documents.length} DOCUMENTS
            </span>
          </div>
        </div>
        <div>
          <input
            id="header-upload"
            type="file"
            className="hidden"
            accept=".pdf,.docx"
            multiple
            onChange={handleFileSelect}
          />
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              onClick={() => document.getElementById('header-upload')?.click()}
              className="bg-primary/20 border border-primary/50 hover:bg-primary/30 hover:glow-teal transition-all duration-300"
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload Document
            </Button>
          </motion.div>
        </div>
      </motion.div>

      {/* Delete Confirmation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{selectedDocument?.filename}</strong>? This action cannot be undone and will remove all associated analysis data.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Document
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Zone */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className={`upload-zone rounded-2xl p-8 text-center transition-all duration-300 ${
          isDragging ? 'drag-active' : ''
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <motion.div
          animate={isDragging ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
          transition={{ type: 'spring' as const, stiffness: 300 }}
        >
          <Upload className={`h-10 w-10 mx-auto mb-4 transition-colors ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
        </motion.div>
        <p className="text-lg font-medium mb-1 text-white">
          {isDragging ? 'Drop files here' : 'Drag and drop files here'}
        </p>
        <p className="text-sm text-muted-foreground mb-4">
          Supports PDF and DOCX files (SOC 2, SIG, HECVAT, etc.)
        </p>
        <div>
          <input
            id="dropzone-upload"
            type="file"
            className="hidden"
            accept=".pdf,.docx"
            multiple
            onChange={handleFileSelect}
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('dropzone-upload')?.click()}
            className="bg-white/5 border-white/10 hover:border-primary/50 hover:bg-primary/10"
          >
            Browse files
          </Button>
        </div>
      </motion.div>

      {uploadError && (
        <div className="mb-6 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {uploadError}
        </div>
      )}

      {uploadMutation.isPending && (
        <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Uploading...
        </div>
      )}

      {/* Search */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Documents List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card className="glass-panel-liquid">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              </motion.div>
              <h3 className="text-lg font-medium mb-2 text-white">No documents yet</h3>
              <p className="text-muted-foreground text-center mb-4">
                Upload your first security report to get started.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-2"
        >
          <AnimatePresence mode="popLayout">
            {documents.map((doc) => (
              <motion.div
                key={doc.id}
                variants={itemVariants}
                layout
                whileHover={{ x: 4 }}
                className="data-row-hover"
              >
                <Card className="glass-panel-liquid border-0">
                  <CardContent className="p-4 flex items-center gap-4">
                    <motion.div
                      whileHover={{ scale: 1.1, rotate: 5 }}
                      className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                        doc.status === 'analyzed' || doc.status === 'processed'
                          ? 'bg-green-500/10 border border-green-500/30'
                          : doc.status === 'failed'
                          ? 'bg-red-500/10 border border-red-500/30'
                          : 'bg-primary/10 border border-primary/30'
                      }`}
                    >
                      <FileText className={`h-5 w-5 ${
                        doc.status === 'analyzed' || doc.status === 'processed'
                          ? 'text-green-500'
                          : doc.status === 'failed'
                          ? 'text-red-500'
                          : 'text-primary'
                      }`} />
                    </motion.div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate text-white">{doc.filename}</p>
                        {getStatusIcon(doc.status)}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                        <Badge variant="outline" className="bg-white/5">{getDocTypeLabel(doc.document_type)}</Badge>
                        <span>{formatFileSize(doc.file_size)}</span>
                        {doc.page_count && <span>{doc.page_count} pages</span>}
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="relative" ref={openMenuId === doc.id ? menuRef : null}>
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        className="rounded-full p-2 hover:bg-white/10 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenMenuId(openMenuId === doc.id ? null : doc.id);
                        }}
                      >
                        <MoreVertical className="h-4 w-4 text-muted-foreground" />
                      </motion.button>
                      <AnimatePresence>
                        {openMenuId === doc.id && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: -10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -10 }}
                            className="absolute right-0 top-full mt-1 w-40 rounded-lg border border-white/10 bg-background/95 backdrop-blur shadow-xl z-50"
                          >
                            <button
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-white hover:bg-white/10 transition-colors rounded-t-lg"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownload(doc);
                              }}
                            >
                              <Download className="h-4 w-4" />
                              Download
                            </button>
                            <button
                              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors rounded-b-lg"
                              onClick={(e) => {
                                e.stopPropagation();
                                openDeleteModal(doc);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                              Delete
                            </button>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}
    </motion.div>
  );
}
