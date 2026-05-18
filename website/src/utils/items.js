import axios from "axios";
import Setting from '@/utils/setting';

/** CJK / Hangul — if present, treat string as non-English display name. */
const CJK_RE = /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]/;

function stripMcFormatCodes(s) {
    return String(s).replace(/§[0-9a-fk-or]/gi, "");
}

/** True if the string is usable as an English (ASCII/Latin) display name. */
function isReadableAsciiName(s) {
    const t = stripMcFormatCodes(String(s)).trim();
    if (!t) return false;
    if (CJK_RE.test(t)) return false;
    return /[A-Za-z]/.test(t);
}

function titleCaseFromRegistryId(name) {
    if (!name) return "";
    const tail = name.includes(":") ? name.slice(name.indexOf(":") + 1) : name;
    const words = tail.replace(/[_.-]+/g, " ").replace(/\s+/g, " ").trim().split(" ");
    const out = words
        .filter(Boolean)
        .map((w) => {
            if (/^\d+$/.test(w)) return w;
            return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
        })
        .join(" ");
    return out || tail;
}

function registryLine(originItem) {
    const d = originItem.damage != null ? originItem.damage : 0;
    return `${originItem.name}:${d}`;
}

/** NESQL `localized_name` that is really an internal id, not a player-facing label. */
function looksLikeInternalItemName(s) {
    const t = stripMcFormatCodes(String(s)).trim();
    if (!t) return true;
    if (/\s/.test(t) && !/^gt\.[a-z0-9_.]+$/i.test(t)) return false;
    return (
        /^(gt\.(metaitem|blockmachines)|item\.|tile\.)/i.test(t)
        || /^[a-z][a-z0-9_.]*\.[a-z0-9_.]+$/i.test(t)
    );
}

/** Prefer NESQL localized name when it is a real in-game label. */
function displayNameFromNesql(nesqlRow, entry, reg) {
    const loc = stripMcFormatCodes(nesqlRow?.localized_name || "").trim();
    if (isReadableAsciiName(loc) && !looksLikeInternalItemName(loc)) {
        return loc;
    }
    const zhRaw = entry?.zh != null ? stripMcFormatCodes(entry.zh) : "";
    if (isReadableAsciiName(zhRaw)) return zhRaw;
    if (reg?.name) {
        const pretty = titleCaseFromRegistryId(reg.name);
        if (isReadableAsciiName(pretty) && pretty !== reg.name) return pretty;
    }
    if (loc) return loc;
    return nesqlRow?.unlocal_name || (reg ? registryLine(reg) : "");
}

/** Build `{ name, damage }` candidates for GTNH NESQL rows → `items_GTNH*.json` keys. */
function registryCandidates(nesqlRow) {
    const mod = String(nesqlRow.mod_id || "").trim();
    const unlocal = String(nesqlRow.unlocal_name || "").trim();
    let damage = nesqlRow.damage != null ? Number(nesqlRow.damage) : 0;
    if (!mod || !unlocal) return [];

    const out = [];
    const seen = new Set();
    const push = (name, dmg) => {
        const key = `${name}\0${dmg}`;
        if (seen.has(key)) return;
        seen.add(key);
        out.push({ name, damage: dmg });
    };

    const modRoots = new Set([mod]);
    if (mod.includes("|")) {
        modRoots.add(mod.split("|")[0]);
        modRoots.add(mod.replace(/\|/g, ""));
    }

    for (const m of modRoots) {
        push(`${m}:${unlocal}`, damage);

        const metaSuffix = unlocal.match(/^gt\.metaitem\.(\d+)\.(\d+)$/);
        if (metaSuffix) {
            const base = `gt.metaitem.${metaSuffix[1]}`;
            const d = Number(metaSuffix[2]);
            push(`${m}:${base}`, d);
            damage = d;
        } else if (/^gt\.metaitem\.\d+$/.test(unlocal)) {
            push(`${m}:${unlocal}`, damage);
        }

        if (unlocal.startsWith("gt.blockmachines.")) {
            push(`${m}:gt.blockmachines`, damage);
        }
        if (unlocal.startsWith("gt.blockmachines2.")) {
            push(`${m}:gt.blockmachines2`, damage);
        }
        if (unlocal.startsWith("gt.blockmachines3.")) {
            push(`${m}:gt.blockmachines3`, damage);
        }

        const parts = unlocal.split(".");
        if (parts[0] === "gt" && parts.length > 2 && !metaSuffix) {
            push(`${m}:${parts[0]}.${parts[1]}`, damage);
        }
        if (unlocal.startsWith("item.") || unlocal.startsWith("tile.")) {
            push(`minecraft:${unlocal}`, damage);
        }
    }
    return out;
}

const itemUtil = {
    items: null,
    fluids: null,
    version: "2.8.0",

    loadWithProgress(url, progressCallback) {
        axios.get(url, {
            onDownloadProgress: (event) => {
                if (event.lengthComputable) {
                    const percentCompleted = Math.round(
                        (event.loaded / event.total) * 100
                    );
                    progressCallback(percentCompleted);
                }
            },
        }).then((res) => {

            progressCallback(100);
        });
    },

    loadItems(progressCallback) {
        if (!this.items) {
            const url = this.itemsJsonUrl();
            axios.get(url, {
                onDownloadProgress: (event) => {
                    if (event.lengthComputable) {
                        const percentCompleted = Math.round((event.loaded / event.total) * 100);
                        if(progressCallback) progressCallback(percentCompleted);  // upload progress
                    }
                },
            }).then((res) => {
                // HTTP status handling
                if (res.status === 200) {
                    this.items = res.data;
                    if(progressCallback) progressCallback(100);
                } else {
                    console.error(`Error loading items: ${res.status}`);
                    if(progressCallback) progressCallback(-1);
                }
            }).catch((error) => {
                console.error("Error loading items:", error);
                if(progressCallback) progressCallback(-1);
            });
        } else {
            if(progressCallback) progressCallback(100);
        }
    },

    loadFluids(progressCallback) {
        if (!this.fluids) {
            const url = this.fluidsJsonUrl();
            axios.get(url, {
                onDownloadProgress: (event) => {
                    if (event.lengthComputable) {
                        const percentCompleted = Math.round((event.loaded / event.total) * 100);
                        if(progressCallback) progressCallback(percentCompleted);
                    }
                },
            }).then((res) => {
                // HTTP status handling
                if (res.status === 200) {
                    this.fluids = res.data;
                    if(progressCallback) progressCallback(100);
                } else {
                    console.error(`Error loading fluids: ${res.status}`);
                    if(progressCallback) progressCallback(-1);
                }
            }).catch((error) => {
                console.error("Error loading fluids:", error);
                if(progressCallback) progressCallback(-1);
            });
        } else {
            if(progressCallback) progressCallback(100);
        }
    },

    isItem: (obj) => {
        return obj && obj["name"] && obj["damage"] !== null;
    },

    getItem(obj) {
        if (this.isItem(obj)) {
            const items = this.items;
            if (!items) return null;
            let name = obj["name"];
            if (!items[name]) {
                name = name.replaceAll("|", "_");
                if (!items[name]) return null;
            }
            const damage = (obj["damage"] != null ? obj["damage"] : 0) + "";
            const exact = items[name][damage];
            if (exact) return exact;
            const dmgNum = Number(damage);
            if (dmgNum > 0) return null;
            return items[name]["0"] || null;
        }
        return null;
    },

    /** Map a NESQL row (`mod_id`, `unlocal_name`, `damage`) to ME/registry `{ name, damage }`. */
    nesqlToRegistry(nesqlRow) {
        if (!nesqlRow || !this.items) return null;
        const mod = String(nesqlRow.mod_id || "").trim();
        const unlocal = String(nesqlRow.unlocal_name || "").trim();
        if (!mod || !unlocal) return null;

        for (const cand of registryCandidates(nesqlRow)) {
            if (this.getItem(cand)) return cand;
        }
        return { name: `${mod}:${unlocal}`, damage: nesqlRow.damage != null ? Number(nesqlRow.damage) : 0 };
    },

    /** Resolved catalog entry + icon URL for a NESQL item row (after `loadItems`). */
    fromNesqlItem(nesqlRow) {
        const reg = this.nesqlToRegistry(nesqlRow);
        if (!reg) return null;
        const entry = this.getItem(reg);
        return {
            registry: reg,
            entry,
            image: this.getItemIcon(entry),
            title: displayNameFromNesql(nesqlRow, entry, reg),
            subtitle: registryLine(reg),
        };
    },

    /** Display label for wiki tables / dialogs (NESQL row). */
    nesqlDisplayName(nesqlRow) {
        if (!nesqlRow) return "";
        if (!this.items) {
            const loc = stripMcFormatCodes(nesqlRow.localized_name || "").trim();
            return loc || nesqlRow.unlocal_name || "";
        }
        return this.fromNesqlItem(nesqlRow)?.title
            || stripMcFormatCodes(nesqlRow.localized_name || "").trim()
            || nesqlRow.unlocal_name
            || "";
    },

    /**
     * Display name for ME items: English/Latin only (ignores UI i18n).
     * Prefers ME label when it is already Latin; otherwise JSON `zh` if Latin;
     * else a readable form derived from the registry id.
     */
    getName(item, originItem, data) {
        const labelRaw = originItem.label != null ? stripMcFormatCodes(originItem.label) : "";
        const zhRaw = item && item.zh != null ? stripMcFormatCodes(item.zh) : "";

        if (originItem.name === "ae2fc:fluid_drop") {
            let name = "";
            if (data && data.tag) {
                try {
                    const tag = JSON.parse(data.tag);
                    const fluidId = tag.value.Fluid.value;
                    const rec = this.fluids && this.fluids[fluidId];
                    const cand = rec && rec.zh;
                    if (cand && isReadableAsciiName(cand)) {
                        name = cand;
                    } else if (isReadableAsciiName(labelRaw)) {
                        name = labelRaw.replace(/^drop of\s+/i, "").trim();
                    } else {
                        name = titleCaseFromRegistryId(String(fluidId).replace(/:/g, "_"));
                    }
                } catch {
                    name = isReadableAsciiName(labelRaw)
                        ? labelRaw.replace(/^drop of\s+/i, "").trim()
                        : titleCaseFromRegistryId(originItem.name);
                }
            } else {
                name = isReadableAsciiName(labelRaw)
                    ? labelRaw.replace(/^drop of\s+/i, "").trim()
                    : titleCaseFromRegistryId(originItem.name);
            }
            return name;
        }

        let name = "";
        if (isReadableAsciiName(labelRaw)) {
            name = labelRaw;
        } else if (isReadableAsciiName(zhRaw)) {
            name = zhRaw;
        } else {
            const pretty = titleCaseFromRegistryId(originItem.name);
            name = pretty && pretty !== originItem.name ? pretty : registryLine(originItem);
        }

        if (
            originItem.name === "minecraft:paper" &&
            labelRaw &&
            stripMcFormatCodes(originItem.label) !== "Paper" &&
            name !== labelRaw
        ) {
            name = `${name} (${labelRaw})`;
        }
        return name;
    },

    /** Second line on item cards: registry id (always ASCII). */
    getRegistrySubtitle(originItem) {
        return registryLine(originItem);
    },

    /** Root-absolute URL for static assets (SPA routes must not use relative `img/...`). */
    staticAsset(path) {
        const p = path.startsWith("/") ? path : `/${path}`;
        const base = String(Setting.get("resourceUrl") || "").replace(/\/$/, "");
        return base ? `${base}${p}` : p;
    },

    itemsJsonUrl() {
        const version = this.version.replace(/\./g, "");
        const suffix = Setting.get("useGzip") ? ".json.gz" : ".json";
        return this.staticAsset(`/items_GTNH${version}${suffix}`);
    },

    fluidsJsonUrl() {
        const version = this.version.replace(/\./g, "");
        const suffix = Setting.get("useGzip") ? ".json.gz" : ".json";
        return this.staticAsset(`/fluids_GTNH${version}${suffix}`);
    },

    getItemIcon(item) {
        if (item && item.img_path) {
            return this.staticAsset(`img/items/${item.img_path}`);
        }
        return this.staticAsset("img/default.png");
    },

    getFluidIcon(data) {
        if (data?.tag) {
            try {
                const tag = JSON.parse(data.tag);
                const fluidId = tag.value.Fluid.value;
                return this.staticAsset(`img/fluids/${fluidId}.png`);
            } catch {
                return this.staticAsset("img/default.png");
            }
        }
        return this.staticAsset("img/default.png");
    },
};

export default itemUtil;