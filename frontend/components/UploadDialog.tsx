"use client";

import { useEffect, useRef, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  uploadDocument, listPersonalDocs, type UploadResponse, type PersonalDoc,
} from "@/lib/api";
import { UploadCloud, FileText, Loader2, CheckCircle2 } from "lucide-react";

type Props = {
  athleteId: string;
  onUploaded?: () => void;
  children?: React.ReactNode;
};

const ACCEPTED = ".pdf,.html,.htm,.txt,.md";

export function UploadDialog({ athleteId, onUploaded, children }: Props) {
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<PersonalDoc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<UploadResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const refreshList = () => {
    listPersonalDocs(athleteId)
      .then((r) => setFiles(r.files || []))
      .catch(() => setFiles([]));
  };

  useEffect(() => {
    if (open) refreshList();
  }, [open, athleteId]);

  const doUpload = async (file: File) => {
    setErr(null);
    setLastResult(null);
    setUploading(true);
    setProgress(`Yükleniyor: ${file.name}`);
    try {
      const r = await uploadDocument(athleteId, file);
      setLastResult(r);
      setProgress(null);
      refreshList();
      onUploaded?.();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setProgress(null);
    } finally {
      setUploading(false);
    }
  };

  const onPick = (f: File | null) => {
    if (!f) return;
    if (f.size > 10 * 1024 * 1024) {
      setErr("Dosya çok büyük (maks 10 MB).");
      return;
    }
    doUpload(f);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Kişisel Doküman Yükle</DialogTitle>
          <DialogDescription>
            Antrenman planı, kan tahlili, koç notları, kişiye özel rehber — TulparAI
            ileride senin için onları da kullanır (per-athlete RAG).
          </DialogDescription>
        </DialogHeader>

        {/* Drag/drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0];
            if (f) onPick(f);
          }}
          onClick={() => inputRef.current?.click()}
          className={`mt-2 rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
            dragOver
              ? "border-primary bg-primary/10"
              : "border-border hover:border-primary/50 hover:bg-card/50"
          }`}
        >
          <UploadCloud className="mx-auto w-10 h-10 text-muted-foreground mb-3" />
          <p className="text-sm font-medium">Dosyayı buraya sürükle veya tıkla</p>
          <p className="text-xs text-muted-foreground mt-1">
            PDF, TXT, MD, HTML &middot; maks 10 MB
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={(e) => {
              onPick(e.target.files?.[0] ?? null);
              e.target.value = "";
            }}
          />
        </div>

        {progress && (
          <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> {progress}
          </div>
        )}
        {err && (
          <div className="mt-3 text-sm text-destructive">{err}</div>
        )}
        {lastResult && (
          <div className="mt-3 flex items-start gap-2 text-sm rounded-lg border border-primary/30 bg-primary/5 p-3">
            <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 shrink-0" />
            <div>
              <div className="font-medium">{lastResult.filename}</div>
              <div className="text-xs text-muted-foreground">
                {lastResult.chunks_indexed} parça indekslendi · {lastResult.sport_tag} ·{" "}
                {lastResult.text_length.toLocaleString()} karakter
              </div>
            </div>
          </div>
        )}

        {/* Already uploaded */}
        {files.length > 0 && (
          <section className="mt-4">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
              Senin Dökümanların ({files.length})
            </h3>
            <ul className="space-y-1 max-h-40 overflow-y-auto">
              {files.map((f) => (
                <li key={f.source_name} className="flex items-center gap-2 text-sm rounded border border-border/60 bg-card/40 p-2 w-full min-w-0">
                  <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                  <span className="truncate flex-1 min-w-0" title={f.source_name}>{f.source_name}</span>
                  <span className="text-xs text-muted-foreground shrink-0">{f.chunks} chunk</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <DialogFooter className="mt-2">
          <Button variant="ghost" onClick={() => setOpen(false)} disabled={uploading}>
            Kapat
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
