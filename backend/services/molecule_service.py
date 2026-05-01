import json
import pickle
from functools import lru_cache

from backend import config


class MoleculeError(Exception):
    pass


@lru_cache(maxsize=1)
def _load_rdkit_modules():
    try:
        from rdkit import Chem
        from rdkit.Chem import rdDepictor
        from rdkit.Chem import rdMolDescriptors
        from rdkit.Chem.Draw import rdMolDraw2D
    except ImportError as exc:
        raise MoleculeError(
            "RDKit is required for molecule rendering but is not installed in this Python environment."
        ) from exc

    return Chem, rdDepictor, rdMolDescriptors, rdMolDraw2D


@lru_cache(maxsize=1)
def _load_aliases():
    if not config.MOLECULE_ALIASES_PATH.is_file():
        return {}
    with config.MOLECULE_ALIASES_PATH.open("r", encoding="utf-8") as handle:
        aliases = json.load(handle)
    return {int(key): int(value) for key, value in aliases.items()}


@lru_cache(maxsize=1)
def _load_pickle_molecules():
    if not config.DRUG_MOLS_PATH.is_file():
        return {}
    with config.DRUG_MOLS_PATH.open("rb") as handle:
        molecules = pickle.load(handle)
    return {int(key): value for key, value in molecules.items() if value is not None}


@lru_cache(maxsize=1)
def _load_sdf_molecules():
    if not config.SDF_PATH.is_file():
        return {}

    Chem, _rdDepictor, _rdMolDescriptors, _rdMolDraw2D = _load_rdkit_modules()
    molecules = {}
    supplier = Chem.SDMolSupplier(str(config.SDF_PATH), sanitize=False, removeHs=False)
    for molecule in supplier:
        if molecule is None or not molecule.HasProp("NSC"):
            continue
        try:
            nsc = int(str(molecule.GetProp("NSC")).strip())
        except ValueError:
            continue
        molecules[nsc] = molecule
    return molecules


def _parse_nsc(nsc):
    try:
        return int(str(nsc).strip())
    except (TypeError, ValueError):
        raise MoleculeError(f"NSC must be a valid integer: {nsc}")


def _resolve_candidates(requested_nsc):
    aliases = _load_aliases()
    candidates = [requested_nsc]
    alias_nsc = aliases.get(requested_nsc)
    if alias_nsc is not None and alias_nsc != requested_nsc:
        candidates.append(alias_nsc)
    return candidates


def _prepare_molecule(molecule):
    Chem, rdDepictor, _rdMolDescriptors, _rdMolDraw2D = _load_rdkit_modules()
    prepared = Chem.Mol(molecule)
    try:
        Chem.SanitizeMol(prepared)
    except Exception as exc:
        raise MoleculeError(f"RDKit sanitization failed: {exc}")

    try:
        rdDepictor.Compute2DCoords(prepared)
    except Exception as exc:
        raise MoleculeError(f"RDKit 2D coordinate generation failed: {exc}")

    return prepared


def _molecule_to_svg(molecule):
    _Chem, _rdDepictor, _rdMolDescriptors, rdMolDraw2D = _load_rdkit_modules()
    drawer = rdMolDraw2D.MolDraw2DSVG(420, 300)
    options = drawer.drawOptions()
    options.clearBackground = False
    drawer.DrawMolecule(molecule)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def _lookup_molecule(requested_nsc):
    candidates = _resolve_candidates(requested_nsc)
    pickle_molecules = _load_pickle_molecules()
    for candidate in candidates:
        molecule = pickle_molecules.get(candidate)
        if molecule is not None:
            return candidate, molecule, "drug_mols.pkl"

    sdf_molecules = _load_sdf_molecules()
    for candidate in candidates:
        molecule = sdf_molecules.get(candidate)
        if molecule is not None:
            return candidate, molecule, "ComboCompoundSet.sdf"

    return candidates[-1], None, None


def get_molecule(nsc):
    # Molecule data flow:
    # user NSC input -> alias resolution -> molecule lookup from pickle/SDF
    # -> RDKit sanitization and SVG generation -> JSON-ready response.
    requested_nsc = _parse_nsc(nsc)
    try:
        Chem, _rdDepictor, rdMolDescriptors, _rdMolDraw2D = _load_rdkit_modules()
    except MoleculeError as exc:
        return {
            "status": "error",
            "requested_nsc": requested_nsc,
            "resolved_nsc": requested_nsc,
            "used_alias": False,
            "alias_used": False,
            "source": None,
            "molecule_found": False,
            "found": False,
            "svg": None,
            "smiles": None,
            "molecular_formula": None,
            "error": str(exc),
        }

    resolved_nsc, molecule, source = _lookup_molecule(requested_nsc)
    used_alias = requested_nsc != resolved_nsc

    if molecule is None:
        return {
            "status": "error",
            "requested_nsc": requested_nsc,
            "resolved_nsc": resolved_nsc,
            "used_alias": used_alias,
            "alias_used": used_alias,
            "source": None,
            "molecule_found": False,
            "found": False,
            "svg": None,
            "smiles": None,
            "molecular_formula": None,
            "error": f"Molecule not found for NSC {requested_nsc}",
        }

    try:
        prepared = _prepare_molecule(molecule)
        smiles = Chem.MolToSmiles(prepared)
        molecular_formula = rdMolDescriptors.CalcMolFormula(prepared)
        svg = _molecule_to_svg(prepared)
    except MoleculeError as exc:
        return {
            "status": "error",
            "requested_nsc": requested_nsc,
            "resolved_nsc": resolved_nsc,
            "used_alias": used_alias,
            "alias_used": used_alias,
            "source": source,
            "molecule_found": False,
            "found": False,
            "svg": None,
            "smiles": None,
            "molecular_formula": None,
            "error": str(exc),
        }

    return {
        "status": "success",
        "requested_nsc": requested_nsc,
        "resolved_nsc": resolved_nsc,
        "used_alias": used_alias,
        "alias_used": used_alias,
        "source": source,
        "molecule_found": True,
        "found": True,
        "svg": svg,
        "smiles": smiles,
        "molecular_formula": molecular_formula,
        "error": None,
    }


def get_two_molecules(payload):
    if not isinstance(payload, dict):
        raise MoleculeError("Request body must be a JSON object.")

    if payload.get("NSC1") is None or str(payload.get("NSC1")).strip() == "":
        raise MoleculeError("NSC1 is required.")
    if payload.get("NSC2") is None or str(payload.get("NSC2")).strip() == "":
        raise MoleculeError("NSC2 is required.")

    molecule_1 = get_molecule(payload.get("NSC1"))
    molecule_2 = get_molecule(payload.get("NSC2"))
    status = "success" if molecule_1["molecule_found"] and molecule_2["molecule_found"] else "error"
    return {
        "status": status,
        "molecule_1": molecule_1,
        "molecule_2": molecule_2,
    }


def get_molecule_pair(payload):
    if not isinstance(payload, dict):
        raise MoleculeError("Request body must be a JSON object.")

    if payload.get("NSC1") is None or str(payload.get("NSC1")).strip() == "":
        raise MoleculeError("NSC1 is required.")
    if payload.get("NSC2") is None or str(payload.get("NSC2")).strip() == "":
        raise MoleculeError("NSC2 is required.")

    molecule_1 = get_molecule(payload.get("NSC1"))
    molecule_2 = get_molecule(payload.get("NSC2"))
    status = "success" if molecule_1["molecule_found"] and molecule_2["molecule_found"] else "error"
    return {
        "status": status,
        "NSC1": molecule_1,
        "NSC2": molecule_2,
    }
