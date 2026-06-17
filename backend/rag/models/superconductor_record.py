"""
SuperconductorRecord — 超导数据记录表（核心表）。

保存某个超导体在某个压力、空间群、计算/实验条件下的具体稳定性和超导性质。
一条记录 = 同一 superconductor + pressure_gpa + space_group 下的一组结果。

Tc 字段设计为多列（McMillan / Allen-Dynes / Eliashberg / 实验），
而非拆成多行——这样可以清晰区分不同方法算出的 Tc 值。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag.database import Base


class SuperconductorRecord(Base):
    __tablename__ = "superconductor_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 归属和来源 ──────────────────────────────────────────────────────
    superconductor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("superconductors.id"), nullable=False, index=True
    )
    paper_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("papers.id"), nullable=True, index=True,
        comment="来自论文时指向 papers.id；来自数据库/人工整理时为空",
    )
    source_label: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="人工指定的自由文本来源，例如 paper / Alexandria / HTSC-2025 / AI筛选数据库",
    )
    article_type: Mapped[str | None] = mapped_column(
        String(1), nullable=True, comment="数据类型: e(实验) / t(理论) / null"
    )
    superconductor_type: Mapped[str | None] = mapped_column(
        String(4), nullable=True, comment="超导体分类: h(氢化物)/c(铜氧化物)/i(铁基)/n(镍基)/cb(碳基)/or(有机)/ot(其他)"
    )

    # ── 结构和压力 ──────────────────────────────────────────────────────
    pressure_gpa: Mapped[float | None] = mapped_column(Float, nullable=True, comment="压力 (GPa)")
    space_group_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="空间群符号，如 Fm-3m")
    space_group_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="空间群编号，如 225")
    crystal_structure: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="晶体结构描述，如 cubic、tetragonal")

    # ── 稳定性 ──────────────────────────────────────────────────────────
    thermodynamically_stable: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="热力学稳定")
    dynamically_stable: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="动力学稳定（无声子虚频）")
    energy_above_hull: Mapped[float | None] = mapped_column(Float, nullable=True, comment="凸包上方能量 (meV/atom)")

    # ── 超导转变温度 Tc ─────────────────────────────────────────────────
    mcmillan_tc: Mapped[float | None] = mapped_column(Float, nullable=True, comment="McMillan 公式 Tc (K)")
    allen_dynes_tc: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Allen-Dynes 修正 Tc (K)")
    isotropic_eliashberg_tc: Mapped[float | None] = mapped_column(Float, nullable=True, comment="各向同性 Eliashberg 方程 Tc (K)")
    anisotropic_eliashberg_tc: Mapped[float | None] = mapped_column(Float, nullable=True, comment="各向异性 Eliashberg 方程 Tc (K)")
    experimental_tc: Mapped[float | None] = mapped_column(Float, nullable=True, comment="实验测量 Tc (K)")

    # ── 电声和电子参数 ──────────────────────────────────────────────────
    lambda_value: Mapped[float | None] = mapped_column(Float, nullable=True, comment="电声耦合常数 λ（无量纲）")
    omega_log: Mapped[float | None] = mapped_column(Float, nullable=True, comment="对数平均声子频率 ω_log (K)")
    n_ef_total: Mapped[float | None] = mapped_column(Float, nullable=True, comment="费米面总态密度 N(Ef) (states/eV/f.u.)")
    element_n_ef: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="元素分解态密度 JSON，如 {'La': 0.2, 'H': 1.8}"
    )

    # ── 赝势和计算设置 ──────────────────────────────────────────────────
    pseudopotential_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="赝势类型，如 PAW、USPP")
    pseudopotential_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="赝势文件名")
    exchange_correlation_functional: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="交换关联泛函，如 PBE、PBEsol")
    calculation_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="计算软件，如 Quantum ESPRESSO、VASP")
    k_grid: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="K 点网格，如 16x16x16")
    q_grid: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Q 点网格，如 4x4x4")
    energy_cutoff_value: Mapped[float | None] = mapped_column(Float, nullable=True, comment="截断能数值")
    energy_cutoff_unit: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="截断能单位，如 Ry、eV")

    # ── 图表控制 ────────────────────────────────────────────────────────
    show_in_chart: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="是否进入 Tc-Pressure 和 Tc-Year 散点图",
    )
    s_factor: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="S 因子 = Tc / sqrt(1521 + P²)"
    )

    # ── 方法和备注 ──────────────────────────────────────────────────────
    method: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Tc 计算方法，如 McMillan / Allen-Dynes / Eliashberg")
    data_source_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="数据来源备注，如 estimated from BCS / inferred from Figure 3(d) / 范围值说明"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── 关系 ────────────────────────────────────────────────────────────
    superconductor = relationship("Superconductor", back_populates="records")
    paper = relationship("Paper", back_populates="records")

    def __repr__(self) -> str:
        return (
            f"<SuperconductorRecord "
            f"superconductor_id={self.superconductor_id} "
            f"P={self.pressure_gpa}GPa "
            f"Tc={self.experimental_tc or self.allen_dynes_tc or self.mcmillan_tc}K>"
        )
