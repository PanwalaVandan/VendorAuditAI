import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Layers, Trash2, Pencil, Play, X, ChevronDown, ChevronUp, Copy } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/components/ui';
import apiClient, { getApiErrorMessage } from '@/lib/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface CustomControl {
  id: string;
  framework_id: string;
  control_id: string;
  name: string;
  description: string;
  category: string | null;
  guidance: string | null;
  order_index: number;
  created_at: string;
  updated_at: string;
}

interface CustomFramework {
  id: string;
  organization_id: string;
  created_by: string;
  name: string;
  version: string;
  description: string | null;
  is_active: boolean;
  controls: CustomControl[];
  created_at: string;
  updated_at: string;
}

interface FrameworkSummary {
  id: string;
  name: string;
  version: string;
  description: string | null;
  is_active: boolean;
  control_count: number;
  created_at: string;
  updated_at: string;
}

// Starter controls to pre-populate when cloning a built-in
const BUILTIN_STARTER_CONTROLS: Record<string, Array<{ control_id: string; name: string; description: string; category: string }>> = {
  soc2_tsc: [
    { control_id: 'CC1.1', name: 'Control Environment', description: 'The entity demonstrates a commitment to integrity and ethical values.', category: 'Common Criteria' },
    { control_id: 'CC2.1', name: 'Communication of Objectives', description: 'Management communicates information relevant to meeting objectives.', category: 'Common Criteria' },
    { control_id: 'CC6.1', name: 'Logical Access Controls', description: 'Logical access security software and infrastructure protect against threats.', category: 'Security' },
  ],
  nist_800_53: [
    { control_id: 'AC-1', name: 'Access Control Policy', description: 'Develop, document, and disseminate an access control policy.', category: 'Access Control' },
    { control_id: 'AU-2', name: 'Audit Events', description: 'Identify the types of events that the system is capable of logging.', category: 'Audit & Accountability' },
    { control_id: 'IR-4', name: 'Incident Handling', description: 'Implement an incident handling capability for security incidents.', category: 'Incident Response' },
  ],
  iso_27001: [
    { control_id: 'A.5.1', name: 'Information Security Policies', description: 'Policies for information security shall be defined and approved by management.', category: 'Policies' },
    { control_id: 'A.9.1', name: 'Access Control Policy', description: 'An access control policy shall be established, documented and reviewed.', category: 'Access Control' },
    { control_id: 'A.12.1', name: 'Operational Procedures', description: 'Operating procedures shall be documented and made available to users.', category: 'Operations' },
  ],
};

const BUILTIN_LABELS: Record<string, string> = {
  soc2_tsc: 'SOC 2 TSC',
  nist_800_53: 'NIST 800-53',
  iso_27001: 'ISO 27001',
  cis_controls: 'CIS Controls',
  hipaa: 'HIPAA',
  pci_dss: 'PCI-DSS',
};

// ── Empty blank control for the add-control form ─────────────────────────────
const BLANK_CONTROL = { control_id: '', name: '', description: '', category: '', guidance: '', order_index: 0 };

// ── Animation variants ───────────────────────────────────────────────────────
const container = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const item = { hidden: { y: 16, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { type: 'spring' as const, stiffness: 100 } } };

// ── Component ────────────────────────────────────────────────────────────────

export function Frameworks() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Which framework is open for editing (null = list view)
  const [editingId, setEditingId] = useState<string | null>(null);
  // Show create form
  const [showCreate, setShowCreate] = useState(false);
  // Create form state
  const [createForm, setCreateForm] = useState({ name: '', version: '1.0', description: '' });
  const [createError, setCreateError] = useState<string | null>(null);
  // Clone modal
  const [showClone, setShowClone] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<string>('soc2_tsc');
  // Control form
  const [controlForm, setControlForm] = useState({ ...BLANK_CONTROL });
  const [editingControlId, setEditingControlId] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [expandedControls, setExpandedControls] = useState(true);

  // ── Queries ────────────────────────────────────────────────────────────────

  const { data: listData, isLoading } = useQuery({
    queryKey: ['custom-frameworks'],
    queryFn: async () => {
      const res = await apiClient.get('/custom-frameworks');
      return res.data;
    },
  });

  const { data: detailData } = useQuery({
    queryKey: ['custom-framework', editingId],
    queryFn: async () => {
      const res = await apiClient.get(`/custom-frameworks/${editingId}`);
      return res.data as CustomFramework;
    },
    enabled: !!editingId,
  });

  const frameworks: FrameworkSummary[] = listData?.data || [];
  const detail: CustomFramework | undefined = detailData;

  // ── Mutations ──────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: async (payload: typeof createForm) => {
      const res = await apiClient.post('/custom-frameworks', payload);
      return res.data as CustomFramework;
    },
    onSuccess: (fw) => {
      queryClient.invalidateQueries({ queryKey: ['custom-frameworks'] });
      setShowCreate(false);
      setCreateForm({ name: '', version: '1.0', description: '' });
      setEditingId(fw.id);
    },
    onError: (e) => setCreateError(getApiErrorMessage(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/custom-frameworks/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-frameworks'] });
      if (editingId) setEditingId(null);
    },
  });

  const updateFrameworkMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<CustomFramework> }) => {
      const res = await apiClient.patch(`/custom-frameworks/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-frameworks'] });
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
    },
  });

  const addControlMutation = useMutation({
    mutationFn: async (payload: typeof controlForm) => {
      const res = await apiClient.post(`/custom-frameworks/${editingId}/controls`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
      setControlForm({ ...BLANK_CONTROL });
      setControlError(null);
    },
    onError: (e) => setControlError(getApiErrorMessage(e)),
  });

  const updateControlMutation = useMutation({
    mutationFn: async ({ controlId, payload }: { controlId: string; payload: Partial<typeof controlForm> }) => {
      const res = await apiClient.patch(`/custom-frameworks/${editingId}/controls/${controlId}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
      setEditingControlId(null);
      setControlForm({ ...BLANK_CONTROL });
      setControlError(null);
    },
    onError: (e) => setControlError(getApiErrorMessage(e)),
  });

  const deleteControlMutation = useMutation({
    mutationFn: async (controlId: string) => {
      await apiClient.delete(`/custom-frameworks/${editingId}/controls/${controlId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] }),
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleCloneApply = () => {
    const starters = BUILTIN_STARTER_CONTROLS[cloneTarget] || [];
    starters.forEach((ctrl, i) => {
      addControlMutation.mutate({ ...BLANK_CONTROL, ...ctrl, order_index: i });
    });
    setShowClone(false);
  };

  const handleControlSubmit = () => {
    if (!controlForm.control_id.trim() || !controlForm.name.trim() || !controlForm.description.trim()) {
      setControlError('Control ID, Name, and Description are required.');
      return;
    }
    if (editingControlId) {
      updateControlMutation.mutate({ controlId: editingControlId, payload: controlForm });
    } else {
      addControlMutation.mutate(controlForm);
    }
  };

  const startEditControl = (ctrl: CustomControl) => {
    setEditingControlId(ctrl.id);
    setControlForm({
      control_id: ctrl.control_id,
      name: ctrl.name,
      description: ctrl.description,
      category: ctrl.category || '',
      guidance: ctrl.guidance || '',
      order_index: ctrl.order_index,
    });
    setControlError(null);
  };

  const cancelControlEdit = () => {
    setEditingControlId(null);
    setControlForm({ ...BLANK_CONTROL });
    setControlError(null);
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  // Detail / edit view
  if (editingId && detail) {
    return (
      <motion.div className="p-8" initial="hidden" animate="visible" variants={container}>
        {/* Header */}
        <motion.div variants={item} className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>← Back</Button>
          <div>
            <h1 className="text-2xl font-bold neon-text">
              EDIT <span className="text-primary">FRAMEWORK</span>
            </h1>
            <p className="text-muted-foreground text-sm">{detail.name} · v{detail.version} · {detail.controls.length} controls</p>
          </div>
          <div className="ml-auto flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/analysis?custom_framework_id=${detail.id}`)}
            >
              <Play className="h-4 w-4 mr-1" />
              Run Analysis
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive border-destructive/40 hover:bg-destructive/10"
              onClick={() => deleteMutation.mutate(detail.id)}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete Framework
            </Button>
          </div>
        </motion.div>

        {/* Framework details */}
        <motion.div variants={item}>
          <Card className="glass-panel-liquid mb-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Pencil className="h-4 w-4" /> Framework Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FrameworkDetailForm
                framework={detail}
                onSave={(payload) => updateFrameworkMutation.mutate({ id: detail.id, payload })}
                isSaving={updateFrameworkMutation.isPending}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Controls */}
        <motion.div variants={item}>
          <Card className="glass-panel-liquid">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Layers className="h-4 w-4" />
                  Controls ({detail.controls.length})
                  <button
                    onClick={() => setExpandedControls(!expandedControls)}
                    className="ml-1 text-muted-foreground hover:text-foreground"
                  >
                    {expandedControls ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                </CardTitle>
                <Button variant="outline" size="sm" onClick={() => setShowClone(true)}>
                  <Copy className="h-4 w-4 mr-1" />
                  Clone from Built-in
                </Button>
              </div>
            </CardHeader>

            <AnimatePresence>
              {expandedControls && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <CardContent>
                    {/* Controls table */}
                    {detail.controls.length > 0 && (
                      <div className="overflow-x-auto rounded-lg border border-border mb-6">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/30">
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">ID</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Name</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Category</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Description</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detail.controls.map((ctrl) => (
                              <tr key={ctrl.id} className="border-b border-border/50 hover:bg-muted/10">
                                <td className="px-4 py-3 font-mono text-primary text-xs">{ctrl.control_id}</td>
                                <td className="px-4 py-3 font-medium">{ctrl.name}</td>
                                <td className="px-4 py-3">
                                  {ctrl.category && (
                                    <span className="text-xs bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-full">
                                      {ctrl.category}
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-3 text-muted-foreground text-xs max-w-xs truncate">{ctrl.description}</td>
                                <td className="px-4 py-3">
                                  <div className="flex gap-2">
                                    <Button variant="ghost" size="sm" onClick={() => startEditControl(ctrl)}>
                                      <Pencil className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-destructive hover:text-destructive"
                                      onClick={() => deleteControlMutation.mutate(ctrl.id)}
                                      disabled={deleteControlMutation.isPending}
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Add / edit control form */}
                    <div className="border border-border rounded-lg p-4 bg-muted/10">
                      <h4 className="text-sm font-semibold mb-3">
                        {editingControlId ? 'Edit Control' : 'Add Control'}
                      </h4>
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">Control ID *</label>
                          <Input
                            placeholder="e.g. CC-1"
                            value={controlForm.control_id}
                            onChange={(e) => setControlForm({ ...controlForm, control_id: e.target.value })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">Category</label>
                          <Input
                            placeholder="e.g. Security"
                            value={controlForm.category}
                            onChange={(e) => setControlForm({ ...controlForm, category: e.target.value })}
                          />
                        </div>
                      </div>
                      <div className="mb-3">
                        <label className="block text-xs text-muted-foreground mb-1">Name *</label>
                        <Input
                          placeholder="Control name"
                          value={controlForm.name}
                          onChange={(e) => setControlForm({ ...controlForm, name: e.target.value })}
                        />
                      </div>
                      <div className="mb-3">
                        <label className="block text-xs text-muted-foreground mb-1">Description *</label>
                        <textarea
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                          rows={3}
                          placeholder="What must be true for this control to pass? The AI uses this to find gaps."
                          value={controlForm.description}
                          onChange={(e) => setControlForm({ ...controlForm, description: e.target.value })}
                        />
                      </div>
                      <div className="mb-3">
                        <label className="block text-xs text-muted-foreground mb-1">Guidance (optional — hints for the AI)</label>
                        <Input
                          placeholder="e.g. Look for: encryption policy, key management, HSM documentation"
                          value={controlForm.guidance}
                          onChange={(e) => setControlForm({ ...controlForm, guidance: e.target.value })}
                        />
                      </div>
                      {controlError && (
                        <p className="text-destructive text-sm mb-3">{controlError}</p>
                      )}
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={handleControlSubmit}
                          disabled={addControlMutation.isPending || updateControlMutation.isPending}
                        >
                          {editingControlId ? 'Update Control' : 'Add Control'}
                        </Button>
                        {editingControlId && (
                          <Button variant="ghost" size="sm" onClick={cancelControlEdit}>Cancel</Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        </motion.div>

        {/* Clone from built-in modal */}
        <AnimatePresence>
          {showClone && (
            <motion.div
              className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="bg-background border border-border rounded-2xl w-[480px] shadow-2xl"
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
              >
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold">Clone from Built-in Framework</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">Adds starter controls — you can edit or remove them</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setShowClone(false)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <div className="p-6 space-y-2">
                  {Object.entries(BUILTIN_LABELS).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setCloneTarget(key)}
                      className={`w-full flex items-center justify-between p-3 rounded-lg border text-sm transition-colors ${
                        cloneTarget === key
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border hover:border-muted-foreground'
                      }`}
                    >
                      <span className="font-medium">{label}</span>
                      <span className="text-xs text-muted-foreground">
                        {BUILTIN_STARTER_CONTROLS[key]?.length ?? 0} starter controls
                      </span>
                    </button>
                  ))}
                  <p className="text-xs text-muted-foreground pt-2">
                    Only a few representative controls are added as starters. Add more manually as needed.
                  </p>
                </div>
                <div className="p-4 border-t border-border flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setShowClone(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleCloneApply}>Add Starter Controls</Button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  // ── List view ────────────────────────────────────────────────────────────────
  return (
    <motion.div className="p-8" initial="hidden" animate="visible" variants={container}>
      {/* Header */}
      <motion.div variants={item} className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold neon-text flex items-center gap-3">
            CUSTOM <span className="text-primary">FRAMEWORKS</span>
            <motion.div
              className="w-2 h-2 rounded-full bg-primary"
              animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </h1>
          <p className="text-muted-foreground mt-1">Build and manage your own compliance frameworks for AI analysis</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Framework
        </Button>
      </motion.div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="mb-6"
          >
            <Card className="glass-panel-liquid border-primary/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span>Create Framework</span>
                  <Button variant="ghost" size="sm" onClick={() => { setShowCreate(false); setCreateError(null); }}>
                    <X className="h-4 w-4" />
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Name *</label>
                    <Input
                      placeholder="e.g. My Custom SOC2"
                      value={createForm.name}
                      onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Version</label>
                    <Input
                      placeholder="1.0"
                      value={createForm.version}
                      onChange={(e) => setCreateForm({ ...createForm, version: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-xs text-muted-foreground mb-1">Description</label>
                  <Input
                    placeholder="What is this framework for?"
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  />
                </div>
                {createError && <p className="text-destructive text-sm mb-3">{createError}</p>}
                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      setCreateError(null);
                      if (!createForm.name.trim()) { setCreateError('Name is required.'); return; }
                      createMutation.mutate(createForm);
                    }}
                    disabled={createMutation.isPending}
                  >
                    {createMutation.isPending ? 'Creating...' : 'Create & Edit'}
                  </Button>
                  <Button variant="ghost" onClick={() => { setShowCreate(false); setCreateError(null); }}>Cancel</Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="glass-panel-liquid animate-pulse">
              <CardContent className="p-6">
                <div className="h-5 bg-muted rounded w-3/4 mb-3" />
                <div className="h-3 bg-muted rounded w-1/2 mb-4" />
                <div className="h-3 bg-muted rounded w-full mb-2" />
                <div className="h-8 bg-muted rounded w-1/3 mt-4" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && frameworks.length === 0 && (
        <motion.div variants={item}>
          <Card className="glass-panel-liquid">
            <CardContent className="flex flex-col items-center justify-center py-20">
              <Layers className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No custom frameworks yet</h3>
              <p className="text-muted-foreground text-center max-w-md mb-6">
                Build your own compliance framework and run AI analysis against your specific controls and requirements.
              </p>
              <Button onClick={() => setShowCreate(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Framework
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Framework cards */}
      {!isLoading && frameworks.length > 0 && (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          variants={container}
        >
          {frameworks.map((fw) => (
            <motion.div key={fw.id} variants={item}>
              <Card className="glass-panel-liquid hover:border-primary/30 transition-colors">
                <CardContent className="p-6">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                      <Layers className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold truncate">{fw.name}</h3>
                      <p className="text-xs text-muted-foreground">v{fw.version}</p>
                    </div>
                  </div>

                  <div className="flex gap-4 text-sm mb-3">
                    <span className="text-muted-foreground">
                      <strong className="text-foreground">{fw.control_count}</strong> controls
                    </span>
                    <span className="text-muted-foreground">
                      {new Date(fw.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {fw.description && (
                    <p className="text-xs text-muted-foreground mb-4 line-clamp-2">{fw.description}</p>
                  )}

                  <div className="flex gap-2 flex-wrap">
                    <Button variant="outline" size="sm" onClick={() => setEditingId(fw.id)}>
                      <Pencil className="h-3.5 w-3.5 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive border-destructive/40 hover:bg-destructive/10"
                      onClick={() => deleteMutation.mutate(fw.id)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      Delete
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => navigate(`/analysis?custom_framework_id=${fw.id}`)}
                    >
                      <Play className="h-3.5 w-3.5 mr-1" />
                      Analyze
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

// ── Framework detail form subcomponent ───────────────────────────────────────

function FrameworkDetailForm({
  framework,
  onSave,
  isSaving,
}: {
  framework: CustomFramework;
  onSave: (payload: { name: string; version: string; description: string | null }) => void;
  isSaving: boolean;
}) {
  const [form, setForm] = useState({
    name: framework.name,
    version: framework.version,
    description: framework.description || '',
  });

  return (
    <div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Name *</label>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Version</label>
          <Input value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-xs text-muted-foreground mb-1">Description</label>
        <Input
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </div>
      <Button
        size="sm"
        onClick={() => onSave({ ...form, description: form.description || null })}
        disabled={isSaving || !form.name.trim()}
      >
        {isSaving ? 'Saving...' : 'Save Details'}
      </Button>
    </div>
  );
}
