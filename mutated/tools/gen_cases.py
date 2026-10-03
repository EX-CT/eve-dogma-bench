#!/usr/bin/env python3
"""Generate mutated/cases/*.json (mutated modules/drones + implant/booster combos) from the 1.8.0 corpus fits.
MIT, no Pyfa code: only the EXCT dataset (mutaplasmid ranges/mappings) and the bench's own cases/*.json are read.
Deterministic (fixed seed). Expected values come from the Pyfa oracle (mutated/tools/make_expected.py).
usage: python3 mutated/tools/gen_cases.py [--dataset PATH]"""
import argparse, collections, copy, glob, gzip, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "mutated" / "cases"
PREF = ["Decayed", "Gravid", "Unstable", "Glorified", "Exigent", "Radical"]


def sig(v, n=6):
    return float(f"{v:.{n}g}")


class G:
    def __init__(self, ds):
        self.d = json.load(gzip.open(ds))
        self.T, self.M, self.E = self.d["types"], self.d["mutaplasmids"], self.d["effects"]
        self.inp = collections.defaultdict(list)          # base type -> [(mutaplasmid, resulting type)]
        for mid, v in sorted(self.M.items(), key=lambda kv: int(kv[0])):
            for mp in v["mapping"]:
                for i in mp["inputs"]:
                    self.inp[i].append((int(mid), mp["output"]))
        self.corpus = {pathlib.Path(f).stem: json.load(open(f)) for f in sorted(glob.glob(str(ROOT / "cases/*.json")))}
        self.rng = random.Random(20261003)
        self.cases = {}
        self.notes = {}
        self.used = collections.Counter()

    def name(self, t):
        return self.T[str(t)]["name"]

    def attr(self, t, a):
        t = self.T[str(t)]
        if a == 4:
            return t["mass"]
        return t["attrs"].get(str(a))

    def mutas(self, base):
        """mutaplasmids for a base type, ordered by PREF tier"""
        out = self.inp.get(base, [])
        return sorted(out, key=lambda mo: next((i for i, p in enumerate(PREF) if self.name(mo[0]).startswith(p)), 9))

    def roll(self, base, muta, how="random", only=None):
        """absolute values by attribute id (string keys). Pyfa compares val/base against the 3-decimal rounded mods."""
        vals = {}
        for a, (lo, hi) in sorted(self.M[str(muta)]["attrs"].items(), key=lambda kv: int(kv[0])):
            if only is not None and int(a) not in only:
                continue
            bv = self.attr(base, int(a))
            if bv is None:
                continue
            lo, hi = round(lo, 3), round(hi, 3)
            m = {"random": lambda: self.rng.uniform(lo, hi), "min": lambda: lo, "max": lambda: hi,
                 "over": lambda: hi + (hi - lo) * 0.5 + 0.05, "under": lambda: lo - (hi - lo) * 0.5 - 0.05}[how]()
            vals[a] = sig(bv * m)
        return vals

    def mutation(self, base, idx=0, how="random", only=None, extra=None):
        mm = self.mutas(base)
        muta, out = mm[idx % len(mm)]
        at = self.roll(base, muta, how, only)
        if extra:
            at.update(extra)
        return out, {"base_type_id": base, "mutaplasmid_type_id": muta, "attributes": at}

    def add(self, name, req, note):
        assert name not in self.cases, name
        self.cases[name] = copy.deepcopy(req)
        self.notes[name] = note

    def plain(self, cn):
        """0 for plain fits (no projected/environment/fleet), so mutated cases test mutation, not other features"""
        r = self.corpus[cn]
        busy = bool(r.get("projected")) + bool((r.get("environment") or {}).get("effect_type_ids")) + \
            bool((r.get("fleet") or {}).get("buffs") or (r.get("fleet") or {}).get("booster_fits"))
        return (busy, 0 if cn.startswith("exct_") else 1)

    def find(self, pred, skip=()):
        """least-used plain corpus fit with a matching unmutated module"""
        best = None
        for cn, r in self.corpus.items():
            if cn in skip:
                continue
            for i, m in enumerate(r["modules"]):
                if pred(m) and not m.get("mutation"):
                    k = (self.plain(cn), self.used[cn], cn)
                    if best is None or k < best[0]:
                        best = (k, cn, r, i)
                    break
        if best is None:
            return None
        self.used[best[1]] += 1
        return best[1:]

    def side_effects(self, booster):
        return [e for e, _ in self.T[str(booster)]["effects"] if "Penalty" in self.E.get(str(e), {}).get("name", "")]


def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")


def build(g):
    used_ships = collections.Counter()
    groups = collections.OrderedDict()
    for cn, r in g.corpus.items():
        for i, m in enumerate(r["modules"]):
            if m["type_id"] in g.inp and not m.get("mutation"):
                groups.setdefault(g.T[str(m["type_id"])]["group"], []).append((cn, i))
    # 1) one random roll per mutable module group (different ships where possible), mutaplasmid tier rotates
    for n, (grp, occ) in enumerate(groups.items()):
        occ.sort(key=lambda ci: (g.plain(ci[0]), used_ships[g.corpus[ci[0]]["ship"]["type_id"]], ci))
        cn, i = occ[0]
        g.used[cn] += 1
        r = copy.deepcopy(g.corpus[cn])
        used_ships[r["ship"]["type_id"]] += 1
        m = r["modules"][i]
        out, mu = g.mutation(m["type_id"], idx=n)
        m["type_id"], m["mutation"] = out, mu
        g.add(f"mm_{slug(g.d['groups'][str(grp)]['name'])}_{cn}", r,
              f"one {g.name(mu['mutaplasmid_type_id'])} roll on {g.name(mu['base_type_id'])} (module {i}) in {cn}")
    # 2) every mutaplasmid tier on one base (MWD), and min/max/clamp edge rolls
    hit = g.find(lambda m: m["type_id"] == 12076)
    cn, r0, i = hit
    for k, (muta, out) in enumerate(g.mutas(12076)):
        for how in (["random", "min", "max", "over", "under"] if k == 0 else ["random"]):
            r = copy.deepcopy(r0)
            m = r["modules"][i]
            at = g.roll(12076, muta, how)
            m["type_id"], m["mutation"] = out, {"base_type_id": 12076, "mutaplasmid_type_id": muta, "attributes": at}
            g.add(f"mwd_{slug(' '.join(w for w in g.name(muta).split()[:2] if not w[0].isdigit()))}_{how}_{cn}", r,
                  f"{g.name(muta)} {how} roll ({'clamped by Pyfa to the range' if how in ('over', 'under') else 'in range'})")
    for base, label in ((2048, "dc"), (3841, "lse"), (3530, "mar")):
        hit = g.find(lambda m, b=base: m["type_id"] == b)
        if not hit:
            continue
        cn, r0, i = hit
        for how in ("min", "max", "over"):
            r = copy.deepcopy(r0)
            m = r["modules"][i]
            out, mu = g.mutation(base, 0, how)
            m["type_id"], m["mutation"] = out, mu
            g.add(f"edge_{label}_{how}_{cn}", r, f"{g.name(mu['mutaplasmid_type_id'])} {how} roll")
    # 3) partial attribute sets (unlisted attributes keep the base value) and attributes the mutaplasmid lacks (ignored)
    for base, label in ((12076, "mwd"), (4405, "dda")):
        hit = g.find(lambda m, b=base: m["type_id"] == b)
        cn, r0, i = hit
        muta, out = g.mutas(base)[0]
        first = int(sorted(g.M[str(muta)]["attrs"], key=int)[0])
        r = copy.deepcopy(r0)
        m = r["modules"][i]
        out, mu = g.mutation(base, 0, "random", only={first})
        m["type_id"], m["mutation"] = out, mu
        g.add(f"partial_{label}_{cn}", r, f"only attribute {first} given; the others keep the base item's value")
        r = copy.deepcopy(r0)
        m = r["modules"][i]
        out, mu = g.mutation(base, 0, "random", extra={"9": 12345.0, "30": sig((g.attr(base, 30) or 1) * 0.5)} if "30" not in g.M[str(muta)]["attrs"] else {"9": 12345.0})
        m["type_id"], m["mutation"] = out, mu
        g.add(f"foreign_attr_{label}_{cn}", r, "attributes the mutaplasmid does not mutate are ignored (Pyfa only reads mutators)")
        r = copy.deepcopy(r0)
        m = r["modules"][i]
        out, mu = g.mutation(base, 0, "random")
        mu["attributes"] = {}
        m["type_id"], m["mutation"] = out, mu
        g.add(f"empty_attrs_{label}_{cn}", r, "mutated type with no rolled values: every mutated attribute = base value")
    # 4) several mutated copies with different rolls (stacking penalties across rolls), states
    for base, label in ((519, "gyro"), (4405, "dda"), (22291, "bcs"), (10190, "mfs")):
        cand = [cn for cn, r0 in g.corpus.items() if sum(m["type_id"] == base for m in r0["modules"]) >= 2]
        if not cand:
            continue
        cn = min(cand, key=lambda c: (g.plain(c), g.used[c], c))
        g.used[cn] += 1
        r0 = g.corpus[cn]
        idx = [i for i, m in enumerate(r0["modules"]) if m["type_id"] == base]
        r = copy.deepcopy(r0)
        for k, i in enumerate(idx):
            out, mu = g.mutation(base, k)
            r["modules"][i]["type_id"], r["modules"][i]["mutation"] = out, mu
        g.add(f"multi_{label}_{cn}", r, f"{len(idx)} mutated {g.name(base)} with different mutaplasmids/rolls")
    for base, label, state in ((12076, "mwd", "overheated"), (527, "web", "overheated"), (3841, "lse", "offline")):
        hit = g.find(lambda m, b=base: m["type_id"] == b)
        cn, r0, i = hit
        r = copy.deepcopy(r0)
        out, mu = g.mutation(base, 1)
        r["modules"][i].update(type_id=out, mutation=mu, state=state)
        g.add(f"state_{label}_{state}_{cn}", r, f"mutated {g.name(base)} {state}")
    # 5) mutated drones
    dr = [(cn, r) for cn, r in g.corpus.items() if any(d["type_id"] in g.inp and not d.get("mutation") for d in r["drones"])]
    dr.sort(key=lambda cr: (g.plain(cr[0]), cr[0]))
    seen = set()
    pick = []
    for cn, r0 in dr:
        t = next(d["type_id"] for d in r0["drones"] if d["type_id"] in g.inp)
        if t not in seen and len(pick) < 6:
            seen.add(t)
            pick.append((cn, r0))
    for k, (cn, r0) in enumerate(pick):
        r = copy.deepcopy(r0)
        j = next(j for j, d in enumerate(r["drones"]) if d["type_id"] in g.inp)
        d = r["drones"][j]
        out, mu = g.mutation(d["type_id"], k)
        q = d["quantity"]
        nd = dict(d, type_id=out, mutation=mu, quantity=1, active=1 if (d.get("active") or 0) > 0 else 0)
        rest = dict(d, quantity=q - 1, active=max(0, (d.get("active") or 0) - 1))
        r["drones"][j:j + 1] = [nd] + ([rest] if q > 1 else [])
        if q > 2:   # a second mutated drone with another roll
            out2, mu2 = g.mutation(d["type_id"], k + 1)
            r["drones"][j + 1]["quantity"] -= 1
            r["drones"][j + 1]["active"] = max(0, r["drones"][j + 1]["active"] - 1)
            r["drones"].insert(j + 1, dict(d, type_id=out2, mutation=mu2, quantity=1, active=1))
        g.add(f"drone_{slug(g.name(d['type_id']))}_{cn}", r, f"mutated {g.name(d['type_id'])} next to unmutated ones")
    # 6) implant sets / hardwirings / boosters (+ side effects), alone and with mutated modules
    sets = {"snake": [19540, 19551, 19553, 19554, 19555, 19556], "crystal": [20121, 20157, 20158, 20159, 20160, 20161],
            "halo": [20498, 20500, 20502, 20504, 20506, 20508], "amulet": [20499, 20501, 20503, 20505, 20507, 20509],
            "ascendancy": [33516, 33525, 33526, 33527, 33528, 33529], "asklepian": [42210, 42211, 42212, 42213, 42214, 42215],
            "talisman": [19534, 19535, 19536, 19537, 19538, 19539], "nomad_lg": [33947, 33948, 33949, 33950, 33951, 33952]}
    combos = [  # (label, implant set, set count, boosters, booster side effects?, mutated base type)
        ("snake_mwd", "snake", 6, [], False, 12076), ("snake_partial_mwd", "snake", 3, [], False, 12076),
        ("crystal_xlsb", "crystal", 6, [10156], True, 10842), ("crystal_bluepill", "crystal", 6, [10155], False, 3841),
        ("halo_mwd_xinstinct", "halo", 6, [15459], True, 12076), ("amulet_plate", "amulet", 6, [], False, 20347),
        ("amulet_mar_exile", "amulet", 5, [25349], True, 3530), ("asklepian_mar_exile", "asklepian", 6, [15480], False, 3530),
        ("ascendancy_mwd", "ascendancy", 6, [], False, 12076), ("talisman_neut", "talisman", 6, [], False, 12269),
        ("nomad_ab_mwd", "nomad_lg", 6, [15463], True, 12076), ("drop_gyro", None, 0, [15478], True, 519),
        ("crash_bcs", None, 0, [10152], True, 22291), ("frentix_mfs", None, 0, [15462], True, 10190),
        ("soothsayer_web", None, 0, [10166], True, 527), ("mindflood_capbat", None, 0, [15465], True, 4871),
        ("bluepill_lse", None, 0, [10156], True, 3841), ("exile_mar_se", None, 0, [25349], True, 3530),
        ("crystal_only", "crystal", 6, [], False, None), ("snake_only_xinstinct", "snake", 6, [15459], True, None),
        ("halo_amulet_mixed", "halo", 3, [], False, 20347), ("two_boosters_dda", None, 0, [15466, 15460], True, 4405),
    ]
    for label, st, n, boosters, se, base in combos:
        if base is not None:
            hit = g.find(lambda m, b=base: m["type_id"] == b)
            if not hit:
                print("skip", label)
                continue
            cn, r0, i = hit
            r = copy.deepcopy(r0)
            out, mu = g.mutation(base, len(g.cases))
            r["modules"][i]["type_id"], r["modules"][i]["mutation"] = out, mu
        else:
            cn = "exct_rifter" if "snake" in label else "exct_tengu"
            r = copy.deepcopy(g.corpus[cn])
        imps = list(sets[st][:n]) if st else []
        if label == "halo_amulet_mixed":
            imps = sets["halo"][:3] + sets["amulet"][3:]
        r["implants"] = imps
        r["boosters"] = [{"type_id": b, "side_effects": g.side_effects(b) if se else []} for b in boosters]
        g.add(f"combo_{label}_{cn}", r, f"implants {[g.name(x) for x in imps]}, boosters {[g.name(b) for b in boosters]}"
              f"{' with side effects' if se else ''}{', mutated ' + g.name(base) if base else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="/workspace/exct-eve/data/dataset-3569502.json.gz")
    a = ap.parse_args()
    g = G(a.dataset)
    build(g)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.json"):
        p.unlink()
    for n, r in sorted(g.cases.items()):
        (OUT / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    (ROOT / "mutated" / "index.json").write_text(json.dumps(dict(sorted(g.notes.items())), indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(g.cases)} cases")


if __name__ == "__main__":
    main()
