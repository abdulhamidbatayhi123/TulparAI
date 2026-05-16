"use client";

import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getProfile, upsertProfile } from "@/lib/api";
import { Loader2 } from "lucide-react";

const SPORTS = [
  { id: "football", label: "Futbol", emoji: "⚽" },
  { id: "wrestling", label: "Güreş", emoji: "🤼" },
  { id: "weightlifting", label: "Halter", emoji: "🏋️" },
  { id: "volleyball", label: "Voleybol", emoji: "🏐" },
] as const;

const PHASES = ["preseason", "competition", "offseason", "recovery"] as const;
const GOALS = ["performance", "bulk", "cut", "maintain", "weight_class", "injury_recovery"] as const;
const DIETS = ["omnivore", "halal", "vegetarian", "vegan"] as const;

type Props = {
  athleteId: string;
  /** Called after a successful save so the sidebar can re-fetch the new profile */
  onSaved?: () => void;
  children?: React.ReactNode;
};

export function ProfileDialog({ athleteId, onSaved, children }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setErr(null);
    getProfile(athleteId)
      .then(setProfile)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [open, athleteId]);

  const update = (key: string, value: unknown) =>
    setProfile((p) => ({ ...(p || {}), [key]: value }));

  const updateSp = (key: string, value: unknown) =>
    setProfile((p) => ({
      ...(p || {}),
      sport_profile: { ...(((p?.sport_profile as Record<string, unknown>) || {})), [key]: value },
    }));

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    setErr(null);
    try {
      await upsertProfile({ ...profile, athlete_id: athleteId });
      setOpen(false);
      onSaved?.();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  };

  const sport = (profile?.sport as string) || "football";
  const sp = (profile?.sport_profile as Record<string, unknown>) || {};

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Profilini Düzenle</DialogTitle>
          <DialogDescription>
            Sporcu bilgilerin AI&apos;ya verilen her sorgunun içine enjekte edilir
            (kişiselleştirme için kritik).
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : err ? (
          <div className="text-sm text-destructive py-4">{err}</div>
        ) : profile ? (
          <div className="space-y-4 py-2">
            {/* Identity */}
            <section className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase">Kimlik</label>
              <Input
                placeholder="Ad Soyad"
                value={(profile.name as string) || ""}
                onChange={(e) => update("name", e.target.value)}
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  placeholder="Yaş"
                  value={(profile.age as number) ?? ""}
                  onChange={(e) => update("age", e.target.value ? +e.target.value : null)}
                />
                <select
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={(profile.sex as string) || ""}
                  onChange={(e) => update("sex", e.target.value)}
                >
                  <option value="">Cinsiyet</option>
                  <option value="male">Erkek</option>
                  <option value="female">Kadın</option>
                </select>
              </div>
              <Input
                placeholder="Şehir"
                value={(profile.city as string) || ""}
                onChange={(e) => update("city", e.target.value)}
              />
            </section>

            {/* Sport */}
            <section className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase">Spor</label>
              <div className="grid grid-cols-4 gap-2">
                {SPORTS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => update("sport", s.id)}
                    className={`flex flex-col items-center gap-1 rounded-lg border-2 p-2 text-xs transition-all ${
                      sport === s.id
                        ? "border-primary bg-primary/10"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <span className="text-xl">{s.emoji}</span>
                    <span>{s.label}</span>
                  </button>
                ))}
              </div>
            </section>

            {/* Sport-specific */}
            <section className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase">Spor Detayı</label>
              {sport === "football" && (
                <>
                  <Input
                    placeholder="Pozisyon (forvet/orta saha/defans/kaleci)"
                    value={(sp.position as string) || ""}
                    onChange={(e) => updateSp("position", e.target.value)}
                  />
                  <Input
                    placeholder="Seviye (amatör/yarı-pro/pro/milli)"
                    value={(sp.level as string) || ""}
                    onChange={(e) => updateSp("level", e.target.value)}
                  />
                </>
              )}
              {sport === "wrestling" && (
                <>
                  <Input
                    placeholder="Sıklet (örn 74kg)"
                    value={(sp.weight_class as string) || ""}
                    onChange={(e) => updateSp("weight_class", e.target.value)}
                  />
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={(sp.style as string) || ""}
                    onChange={(e) => updateSp("style", e.target.value)}
                  >
                    <option value="">Stil</option>
                    <option value="freestyle">Serbest</option>
                    <option value="greco-roman">Grekoromen</option>
                  </select>
                </>
              )}
              {sport === "weightlifting" && (
                <>
                  <Input
                    placeholder="Sıklet (örn 89kg)"
                    value={(sp.weight_class as string) || ""}
                    onChange={(e) => updateSp("weight_class", e.target.value)}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      placeholder="Snatch 1RM"
                      value={((sp.current_lifts as { snatch?: number })?.snatch ?? "")}
                      onChange={(e) =>
                        updateSp("current_lifts", {
                          ...((sp.current_lifts as Record<string, unknown>) || {}),
                          snatch: e.target.value ? +e.target.value : null,
                        })
                      }
                    />
                    <Input
                      type="number"
                      placeholder="Clean & Jerk 1RM"
                      value={((sp.current_lifts as { clean_jerk?: number })?.clean_jerk ?? "")}
                      onChange={(e) =>
                        updateSp("current_lifts", {
                          ...((sp.current_lifts as Record<string, unknown>) || {}),
                          clean_jerk: e.target.value ? +e.target.value : null,
                        })
                      }
                    />
                  </div>
                </>
              )}
              {sport === "volleyball" && (
                <>
                  <Input
                    placeholder="Pozisyon (pasör/orta/smaçör/libero/karşı)"
                    value={(sp.position as string) || ""}
                    onChange={(e) => updateSp("position", e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="Smaç erişimi (cm)"
                    value={(sp.spike_reach_cm as number) ?? ""}
                    onChange={(e) => updateSp("spike_reach_cm", e.target.value ? +e.target.value : null)}
                  />
                </>
              )}
            </section>

            {/* Body */}
            <section className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase">Vücut & Antrenman</label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  placeholder="Boy (cm)"
                  value={(profile.height_cm as number) ?? ""}
                  onChange={(e) => update("height_cm", e.target.value ? +e.target.value : null)}
                />
                <Input
                  type="number"
                  placeholder="Kilo (kg)"
                  value={(profile.weight_kg as number) ?? ""}
                  onChange={(e) => update("weight_kg", e.target.value ? +e.target.value : null)}
                />
              </div>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={(profile.training_phase as string) || ""}
                onChange={(e) => update("training_phase", e.target.value)}
              >
                <option value="">Sezon</option>
                {PHASES.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </section>

            {/* Goal + Diet */}
            <section className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase">Hedef & Diyet</label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={(profile.primary_goal as string) || ""}
                onChange={(e) => update("primary_goal", e.target.value)}
              >
                <option value="">Birincil hedef</option>
                {GOALS.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={(profile.diet_type as string) || "omnivore"}
                onChange={(e) => update("diet_type", e.target.value)}
              >
                {DIETS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </section>
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)} disabled={saving}>
            İptal
          </Button>
          <Button onClick={save} disabled={!profile || saving} className="bg-primary text-primary-foreground hover:bg-primary/90">
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Kaydet
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
