// 英文枚举标签。键集必须与 zh/enums.ts 完全一致。
// 专有方法名（McMillan、Allen-Dynes、Eliashberg、SCDFT）两种语言下均保留原文。
export default {
  materialDimensionality: {
    zero_dimensional: 'Zero-dimensional',
    one_dimensional: 'One-dimensional',
    two_dimensional: 'Two-dimensional',
    three_dimensional: 'Three-dimensional',
    quasi_one_dimensional: 'Quasi-one-dimensional',
    quasi_two_dimensional: 'Quasi-two-dimensional',
    unknown: 'Unknown',
  },
  crystalSystem: {
    triclinic: 'Triclinic',
    monoclinic: 'Monoclinic',
    orthorhombic: 'Orthorhombic',
    tetragonal: 'Tetragonal',
    trigonal: 'Trigonal',
    hexagonal: 'Hexagonal',
    cubic: 'Cubic',
    unknown: 'Unknown',
  },
  tcMethod: {
    unknown: 'Unknown',
    experimental: 'Experimental measurement',
    mcmillan: 'McMillan',
    allen_dynes: 'Allen-Dynes-McMillan',
    isotropic_eliashberg: 'isotropic Migdal-Eliashberg',
    anisotropic_eliashberg: 'anisotropic Migdal-Eliashberg',
    scdft: 'SCDFT',
    other: 'Other',
  },
  paperType: {
    theoretical: 'Theoretical',
    experimental: 'Experimental',
    review: 'Review',
    unknown: 'Undetermined',
  },
  theoreticalSubtype: {
    calculation: 'Calculation',
    method: 'Method',
    theory: 'Theory and mechanism',
  },
  superconductorKind: {
    conventional: 'Conventional (BCS) superconductor',
    unconventional: 'Unconventional superconductor',
    unknown: 'Unknown',
  },
  stateKind: {
    theoretical: 'Theoretical',
    experimental: 'Experimental',
    mixed: 'Theoretical and experimental',
    unknown: 'Unknown',
  },
  reviewStatus: {
    pending: 'Pending review',
    approved: 'Approved',
    rejected: 'Rejected',
    needs_revision: 'Pending review (legacy)',
  },
  role: {
    user: 'User',
    admin: 'Administrator',
    superadmin: 'Super administrator',
  },
} as const
