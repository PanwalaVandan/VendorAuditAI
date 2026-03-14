import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Building2,
  Globe,
  Shield,
  FileText,
  AlertTriangle,
  Calendar,
  Tag,
  Database,
  Loader2,
  Pencil,
  Trash2,
  ExternalLink,
  CheckCircle,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Label,
  Input,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui';
import apiClient, { getApiErrorMessage } from '@/lib/api';
import { normalizeFinding } from '@/lib/findings';
import { AIClassificationPanel } from '@/components/vendors/AIClassificationPanel';
import type { Vendor, VendorTier, VendorStatus, Document, Finding, UpdateVendorRequest } from '@/types/api';

// Extended vendor type with categorization fields from backend
interface VendorWithCategorization extends Vendor {
  category?: string;
  recommended_frameworks?: string[];
  data_types?: string[];
  categorization_confidence?: number;
}

export function VendorDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [editVendor, setEditVendor] = useState<UpdateVendorRequest>({
    name: '',
    website: '',
    description: '',
    tier: 'medium',
    status: 'active',
  });

  // Fetch vendor details
  const {
    data: vendor,
    isLoading: isLoadingVendor,
    error: vendorError,
  } = useQuery<VendorWithCategorization>({
    queryKey: ['vendor', id],
    queryFn: async () => {
      const response = await apiClient.get(`/vendors/${id}`);
      return response.data;
    },
    enabled: !!id,
  });

  // Fetch vendor's documents
  const { data: documentsResponse, isLoading: isLoadingDocuments } = useQuery({
    queryKey: ['vendor-documents', id],
    queryFn: async () => {
      const response = await apiClient.get('/documents', {
        params: { vendor_id: id, limit: 50 },
      });
      return response.data;
    },
    enabled: !!id,
  });

  // Fetch vendor's findings
  const { data: findingsResponse, isLoading: isLoadingFindings } = useQuery({
    queryKey: ['vendor-findings', id],
    queryFn: async () => {
      const response = await apiClient.get('/analysis/findings', {
        params: { vendor_id: id, limit: 50 },
      });
      return response.data;
    },
    enabled: !!id,
  });

  const documents: Document[] = documentsResponse?.data || [];
  // Normalize snake_case backend response to camelCase Finding shape
  const findings: Finding[] = (findingsResponse?.data || []).map(normalizeFinding);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async (data: UpdateVendorRequest) => {
      const response = await apiClient.patch(`/vendors/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendor', id] });
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      setShowEditModal(false);
      setEditError(null);
    },
    onError: (error) => {
      setEditError(getApiErrorMessage(error));
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async () => {
      await apiClient.delete(`/vendors/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      navigate('/vendors');
    },
  });

  const openEditModal = () => {
    if (vendor) {
      setEditVendor({
        name: vendor.name,
        website: vendor.website || '',
        description: vendor.description || '',
        tier: vendor.tier,
        status: vendor.status,
      });
      setEditError(null);
      setShowEditModal(true);
    }
  };

  const handleEditVendor = () => {
    if (!editVendor.name?.trim()) {
      setEditError('Vendor name is required');
      return;
    }
    updateMutation.mutate(editVendor);
  };

  const handleDeleteVendor = () => {
    deleteMutation.mutate();
  };

  const getTierVariant = (tier: VendorTier) => {
    switch (tier) {
      case 'critical':
        return 'critical';
      case 'high':
        return 'high';
      case 'medium':
        return 'medium';
      case 'low':
        return 'low';
      default:
        return 'secondary';
    }
  };

  const getStatusColor = (status: VendorStatus) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'inactive':
        return 'text-gray-600 bg-gray-100';
      case 'onboarding':
        return 'text-blue-600 bg-blue-100';
      case 'offboarding':
        return 'text-orange-600 bg-orange-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatCategory = (category: string) => {
    return category
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  // Calculate findings by severity
  const findingsBySeverity = findings.reduce(
    (acc, finding) => {
      acc[finding.severity] = (acc[finding.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  if (isLoadingVendor) {
    return (
      <div className="p-8 flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (vendorError || !vendor) {
    return (
      <div className="p-8">
        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-medium mb-2">Vendor Not Found</h3>
            <p className="text-muted-foreground mb-4">
              {vendorError ? getApiErrorMessage(vendorError) : 'The vendor you are looking for does not exist.'}
            </p>
            <Button onClick={() => navigate('/vendors')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Vendors
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/vendors')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{vendor.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={getTierVariant(vendor.tier)}>{vendor.tier}</Badge>
                <span className={`text-xs px-2 py-1 rounded-full capitalize ${getStatusColor(vendor.status)}`}>
                  {vendor.status}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={openEditModal}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="destructive" onClick={() => setShowDeleteModal(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Edit Modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Edit Vendor</DialogTitle>
            <DialogDescription>Update vendor information and risk classification.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Vendor Name *</Label>
              <Input
                id="edit-name"
                value={editVendor.name || ''}
                onChange={(e) => setEditVendor({ ...editVendor, name: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-website">Website</Label>
              <Input
                id="edit-website"
                value={editVendor.website || ''}
                onChange={(e) => setEditVendor({ ...editVendor, website: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Input
                id="edit-description"
                value={editVendor.description || ''}
                onChange={(e) => setEditVendor({ ...editVendor, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-tier">Risk Tier</Label>
                <select
                  id="edit-tier"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={editVendor.tier || 'medium'}
                  onChange={(e) => setEditVendor({ ...editVendor, tier: e.target.value as VendorTier })}
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-status">Status</Label>
                <select
                  id="edit-status"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={editVendor.status || 'active'}
                  onChange={(e) => setEditVendor({ ...editVendor, status: e.target.value as VendorStatus })}
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="onboarding">Onboarding</option>
                  <option value="offboarding">Offboarding</option>
                </select>
              </div>
            </div>
            {editError && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{editError}</div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditModal(false)}>Cancel</Button>
            <Button onClick={handleEditVendor} disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Vendor</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{vendor.name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteVendor} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Vendor
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Vendor Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Info Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Vendor Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {vendor.description && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Description</label>
                  <p className="mt-1">{vendor.description}</p>
                </div>
              )}
              {vendor.website && (
                <div className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-muted-foreground" />
                  <a
                    href={vendor.website.startsWith('http') ? vendor.website : `https://${vendor.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline flex items-center gap-1"
                  >
                    {vendor.website.replace(/^https?:\/\//, '')}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Last Assessed</label>
                  <p className="mt-1 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {(vendor.last_assessed || vendor.lastAssessed) && !isNaN(new Date(vendor.last_assessed || vendor.lastAssessed || '').getTime())
                      ? new Date(vendor.last_assessed || vendor.lastAssessed || '').toLocaleDateString()
                      : 'Never'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Next Assessment Due</label>
                  <p className="mt-1 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {vendor.nextAssessmentDue && !isNaN(new Date(vendor.nextAssessmentDue).getTime())
                      ? new Date(vendor.nextAssessmentDue).toLocaleDateString()
                      : 'Not scheduled'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Categorization Card */}
          {(vendor.category || vendor.recommended_frameworks || vendor.data_types) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Tag className="h-5 w-5" />
                  Risk Classification
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {vendor.category && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Category</label>
                    <p className="mt-1 text-lg font-medium">{formatCategory(vendor.category)}</p>
                    {vendor.categorization_confidence && (
                      <p className="text-sm text-muted-foreground">
                        Confidence: {Math.round(vendor.categorization_confidence * 100)}%
                      </p>
                    )}
                  </div>
                )}
                {vendor.recommended_frameworks && vendor.recommended_frameworks.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      Recommended Frameworks
                    </label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {vendor.recommended_frameworks.map((fw) => (
                        <Badge key={fw} variant="outline">
                          {fw.toUpperCase()}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {vendor.data_types && vendor.data_types.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Data Types Handled
                    </label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {vendor.data_types.map((dt) => (
                        <Badge key={dt} variant="secondary">
                          {dt.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Documents Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Documents ({documents.length})
              </CardTitle>
              <Button variant="outline" size="sm" onClick={() => navigate(`/documents?vendor_id=${id}`)}>
                Upload Document
              </Button>
            </CardHeader>
            <CardContent>
              {isLoadingDocuments ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No documents uploaded for this vendor</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="font-medium">{doc.originalFilename}</p>
                          <p className="text-sm text-muted-foreground">
                            {doc.docType?.toUpperCase() || 'Document'} - {doc.status}
                          </p>
                        </div>
                      </div>
                      <Badge variant={doc.status === 'processed' ? 'default' : 'secondary'}>
                        {doc.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Findings Summary */}
        <div className="space-y-6">
          {/* AI Classification Panel */}
          <AIClassificationPanel vendorId={vendor.id} vendorName={vendor.name} />

          {/* Findings Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Findings Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingFindings ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : findings.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  <p>No findings for this vendor</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-3xl font-bold">{findings.length} Findings</div>
                  <div className="space-y-2">
                    {['critical', 'high', 'medium', 'low', 'info'].map((severity) => {
                      const count = findingsBySeverity[severity] || 0;
                      const colors = {
                        critical: 'bg-red-500',
                        high: 'bg-orange-500',
                        medium: 'bg-yellow-500',
                        low: 'bg-green-500',
                        info: 'bg-blue-500',
                      };
                      return (
                        <div key={severity} className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${colors[severity as keyof typeof colors]}`} />
                          <span className="capitalize flex-1">{severity}</span>
                          <span className="font-medium">{count}</span>
                        </div>
                      );
                    })}
                  </div>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      // Navigate to analysis pre-selecting the first analyzed document
                      const analyzedDoc = documents.find(
                        (d) => d.status === 'analyzed' || d.status === 'processed'
                      );
                      navigate(
                        analyzedDoc
                          ? `/analysis?document_id=${analyzedDoc.id}`
                          : '/analysis'
                      );
                    }}
                  >
                    View All Findings
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tags Card */}
          {vendor.tags && vendor.tags.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Tag className="h-5 w-5" />
                  Tags
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {vendor.tags.map((tag, index) => (
                    <Badge key={index} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
