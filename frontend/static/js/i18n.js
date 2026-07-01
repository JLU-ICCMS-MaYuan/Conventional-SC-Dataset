/**
 * 中英双语国际化模块
 * Chinese-English Internationalization (i18n) Module
 */
const I18N = {
    lang: localStorage.getItem('lang') || 'zh',

    dict: {
        // ========== Navbar 导航栏 ==========
        'nav.title': { zh: '超导文献数据库', en: 'Superconductor Literature DB' },
        'nav.home': { zh: '首页', en: 'Home' },

        // ========== Index 首页 ==========
        'index.page_title': { zh: '超导文献数据库 - 元素周期表', en: 'Superconductor Literature DB - Periodic Table' },
        'index.title': { zh: '超导文献数据库', en: 'Superconductor Literature Database' },
        'index.subtitle': { zh: '基于元素周期表的超导材料文献检索系统', en: 'Periodic-table-based superconductor literature retrieval system' },
        'index.periodic_table': { zh: '元素周期表', en: 'Periodic Table' },
        'index.selected_elements': { zh: '已选元素：', en: 'Selected: ' },
        'index.none_selected': { zh: '未选择', en: 'None' },
        'index.select_hint': { zh: '点击元素进行选择，选中后再次点击可取消。选择完成后点击下方按钮或按Enter键进入页面。', en: 'Click elements to select, click again to deselect. Press button or Enter to view.' },
        'index.filter_label': { zh: '筛选条件', en: 'Filter Mode' },
        'index.mode_only': { zh: '仅包含选择元素', en: 'Selected Elements Only' },
        'index.mode_combination': { zh: '选择元素的组合', en: 'Combinations of Selected' },
        'index.mode_contains': { zh: '包含所选元素', en: 'Contains Selected Elements' },
        'index.show_compounds': { zh: '进入页面', en: 'View' },
        'index.clear_selection': { zh: '清除选择', en: 'Clear Selection' },
        'index.fast_upload': { zh: '快速上传', en: 'Fast Upload' },
        'index.fast_upload_action': { zh: '🚀 快速上传 (xlsx, csv, txt)', en: '🚀 Fast Upload (xlsx, csv, txt)' },
        'index.fast_upload_example': { zh: '📄 快速上传示例 (.xlsx)', en: '📄 Fast Upload Example (.xlsx)' },
        'index.tc_predict_lab': { zh: '⚡ 超导预测实验', en: '⚡ Tc Prediction Lab' },
        'index.no_compounds': { zh: '暂无数据', en: 'No Data' },
        'index.chart_tc_history': { zh: '超导临界温度 (Tc) 历史演变', en: 'Superconducting Tc Evolution History' },
        'index.chart_tc_pressure': { zh: '数据库实时 P-Tc 分布', en: 'Real-time P-Tc Distribution' },
        'index.chart_contributor_ranking': { zh: '贡献者排行 (Top 20)', en: 'Contributor Ranking (Top 20)' },
        'index.chart_year': { zh: '年份', en: 'Year' },
        'index.chart_tc': { zh: '临界温度 Tc (K)', en: 'Critical Temperature Tc (K)' },
        'index.chart_pressure': { zh: '压强 (GPa)', en: 'Pressure (GPa)' },
        'index.chart_papers': { zh: '篇', en: 'papers' },
        'index.chart_papers_submitted': { zh: '提交文献数', en: 'Papers Submitted' },
        'index.chart_papers_count_label': { zh: '文献提交数量', en: 'Papers Submitted' },
        'index.chart_submitted_papers': { zh: ' 提交了 {count} 篇文献', en: ' submitted {count} papers' },
        'index.legend_experiment': { zh: '实验数据', en: 'Experiment' },
        'index.legend_theory': { zh: '理论预测', en: 'Theory' },
        'index.usage_guide': { zh: '使用说明', en: 'Usage Guide' },
        'index.usage_item_1': { zh: '选择一个或多个元素，系统将显示含有这些元素的超导体文献', en: 'Select one or more elements to find superconductor literature containing them' },
        'index.usage_item_2': { zh: '选择多个元素时，显示同时包含所有选中元素的化合物文献', en: 'When selecting multiple elements, compounds containing ALL selected elements are shown' },
        'index.usage_item_3': { zh: '如果元素组合暂无文献，系统会提示您重新选择', en: 'If no literature exists for the combination, you will be prompted to reselect' },
        'index.usage_item_4': { zh: '支持键盘Enter键快捷跳转', en: 'Press Enter key for quick navigation' },
        'index.login_to_upload': { zh: '只有注册用户可以批量上传文献。是否立即前往登录？', en: 'Only registered users can batch upload. Go to login now?' },
        'index.loading': { zh: '加载中...', en: 'Loading...' },

        // ========== Common 通用 ==========
        'common.language': { zh: '中/EN', en: '中/EN' },
        'common.loading': { zh: '加载中...', en: 'Loading...' },
        'common.error': { zh: '错误', en: 'Error' },
        'common.success': { zh: '成功', en: 'Success' },
        'common.confirm': { zh: '确认', en: 'Confirm' },
        'common.save': { zh: '保存', en: 'Save' },
        'common.cancel': { zh: '取消', en: 'Cancel' },
        'common.close': { zh: '关闭', en: 'Close' },
        'common.edit': { zh: '编辑', en: 'Edit' },
        'common.delete': { zh: '删除', en: 'Delete' },
        'common.submit': { zh: '提交', en: 'Submit' },
        'common.search': { zh: '搜索', en: 'Search' },
        'common.reset': { zh: '重置', en: 'Reset' },
        'common.back_home': { zh: '返回首页', en: 'Back to Home' },
        'common.logout': { zh: '退出', en: 'Logout' },
        'common.welcome': { zh: '欢迎，', en: 'Welcome, ' },
        'common.yes': { zh: '是', en: 'Yes' },
        'common.no': { zh: '否', en: 'No' },
        'common.unknown': { zh: '未知', en: 'Unknown' },
        'common.none': { zh: '无', en: 'None' },
        'common.no_data': { zh: '暂无数据', en: 'No Data' },
        'auth.logged_out': { zh: '已退出登录', en: 'Logged out' },
        'common.view_image': { zh: '查看图片', en: 'View Image' },
        'common.prev': { zh: '上一页', en: 'Prev' },
        'common.next': { zh: '下一页', en: 'Next' },
        'common.page_info': { zh: '第 {start}-{end} 条，共 {total} 条', en: '{start}-{end} of {total}' },
        'common.prev_group': { zh: '上一组', en: 'Prev Group' },
        'common.next_group': { zh: '下一组', en: 'Next Group' },

        // ========== Compound 组合页 ==========
        'compound.page_title': { zh: '元素组合 - 超导文献数据库', en: 'Element Combination - Superconductor Literature DB' },
        'compound.loading': { zh: '加载中...', en: 'Loading...' },
        'compound.load_error': { zh: '加载失败', en: 'Load Failed' },
        'compound.no_papers': { zh: '暂无文献', en: 'No Papers' },
        'compound.back_to_table': { zh: '返回元素周期表', en: 'Back to Periodic Table' },
        'compound.upload_paper': { zh: '上传文献', en: 'Upload Paper' },
        'compound.review_filter': { zh: '审核状态筛选', en: 'Review Status Filter' },
        'compound.all': { zh: '全部', en: 'All' },
        'compound.approved': { zh: '已通过', en: 'Approved' },
        'compound.unreviewed': { zh: '未审核', en: 'Unreviewed' },
        'compound.rejected': { zh: '已拒绝', en: 'Rejected' },
        'compound.database': { zh: '数据库', en: 'Database' },
        'compound.local_db': { zh: '本地数据库', en: 'Local Database' },
        'compound.alexandria_db': { zh: 'Alexandria 电声耦合', en: 'Alexandria EPC' },
        'compound.htsc2025_db': { zh: 'HTSC-2025 常压超导', en: 'HTSC-2025 Ambient-Pressure SC' },
        'compound.ai_db': { zh: 'AI筛选数据库', en: 'AI Filtered DB' },
        'compound.test_db': { zh: '🧪 测试数据库', en: '🧪 Test DB' },
        'compound.local_db_desc': { zh: '用户上传的文献数据', en: 'User-uploaded literature data' },
        'compound.ai_db_desc': { zh: 'AI自动读取整理的文献，结果可能存在误差，仅供参考', en: 'AI-curated literature, results may contain inaccuracies — for reference only' },
        'compound.alexandria_db_desc': { zh: '德国波鸿鲁尔大学电声耦合材料数据库，收录第一性原理计算的超导材料', en: 'Electron-phonon coupling materials database from Ruhr University Bochum, containing DFPT-calculated superconductors' },
        'compound.htsc2025_db_desc': { zh: '常压高温超导基准数据集，收录2023-2025年基于BCS理论预测的超导材料，包含X₂YH₆、钙钛矿MXH₃、M₃XH₈、BCN掺杂及二维类MgB₂体系', en: 'Ambient-pressure high-Tc benchmark dataset (2023-2025) covering BCS-theory-predicted superconductors: X₂YH₆, perovskite MXH₃, M₃XH₈, BCN-doped, and 2D MgB₂-like systems' },
        'compound.search_keyword': { zh: '搜索关键词（标题、作者、化学式）', en: 'Search keywords (title, author, formula)' },
        'compound.year_min': { zh: '最小年份', en: 'Min Year' },
        'compound.year_max': { zh: '最大年份', en: 'Max Year' },
        'compound.min_tc': { zh: '最低 Tc (K)', en: 'Min Tc (K)' },
        'compound.stable_only': { zh: '仅稳定', en: 'Stable Only' },
        'compound.search': { zh: '搜索', en: 'Search' },
        'compound.reset': { zh: '重置', en: 'Reset' },
        'compound.batch_export': { zh: '批量导出', en: 'Batch Export' },
        'compound.export_ris': { zh: '导出为 RIS (.ris)', en: 'Export as RIS (.ris)' },
        'compound.export_json': { zh: '导出为 JSON (.json)', en: 'Export as JSON (.json)' },
        'compound.system_sc': { zh: '系统超导体', en: 'System Superconductor' },
        'compound.loading_papers': { zh: '正在加载文献...', en: 'Loading papers...' },
        'compound.unknown_author': { zh: '未知作者', en: 'Unknown Author' },
        'compound.unknown_year': { zh: '未知年份', en: 'Unknown Year' },
        'compound.unknown_system': { zh: '未知体系', en: 'Unknown System' },
        'compound.corresponding': { zh: '通讯', en: 'Corr.' },
        'compound.author': { zh: '作者', en: 'Author' },
        'compound.journal': { zh: '期刊', en: 'Journal' },
        'compound.abstract': { zh: '摘要', en: 'Abstract' },
        'compound.physical_params': { zh: '物理参数', en: 'Physical Parameters' },
        'compound.crystal_structure': { zh: '空间群', en: 'Space Group' },
        'compound.chemical_formula': { zh: '化学式', en: 'Formula' },
        'compound.is_experimental': { zh: '是否实验合成', en: 'Experimental?' },
        'compound.superconducting_temp': { zh: '超导温度', en: 'Tc' },
        'compound.superconducting_pressure': { zh: '超导压强', en: 'Pressure' },
        'compound.contributor': { zh: '贡献者', en: 'Contributor' },
        'compound.submit_time': { zh: '提交时间', en: 'Submitted' },
        'compound.ris_export': { zh: 'RIS导出', en: 'RIS Export' },
        'compound.view_detail': { zh: '查看原始数据', en: 'View Raw Data' },
        'compound.view_cif': { zh: '查看 CIF 结构', en: 'View CIF Structure' },
        'compound.download_data': { zh: '下载完整数据', en: 'Download Full Data' },
        'compound.unknown_formula': { zh: '未知', en: 'Unknown' },
        'compound.alexandria_title': { zh: 'Alexandria 电声耦合数据库', en: 'Alexandria EPC Database' },
        'compound.htsc2025_title': { zh: 'HTSC-2025 常压超导', en: 'HTSC-2025 Ambient-Pressure SC' },
        'compound.material_count': { zh: '个材料', en: ' materials' },
        'compound.combination_not_found': { zh: '元素组合不存在', en: 'Combination Not Found' },
        'compound.no_physical_data': { zh: '无完整的物理参数数据', en: 'No complete physical data' },
        'compound.no_alexandria': { zh: 'Alexandria 数据库中未找到匹配的电声耦合材料数据', en: 'No matching EPC materials found in Alexandria' },
        'compound.no_htsc2025': { zh: 'HTSC-2025 数据集中未找到匹配的材料', en: 'No matching materials found in HTSC-2025' },
        'compound.stable': { zh: '动力学稳定', en: 'Dynamically Stable' },
        'compound.unstable': { zh: '可能不稳定（虚声子）', en: 'Possibly Unstable (imag. phonons)' },
        'compound.nsites': { zh: '原子数', en: 'N sites' },
        'compound.band_gap': { zh: '带隙', en: 'Band Gap' },
        'compound.page_info': { zh: '第 {start}-{end} 条，共 {total} 条', en: '{start}-{end} of {total}' },
        'compound.page_material_info': { zh: '第 {start}-{end} 个材料，共 {total} 个', en: '{start}-{end} of {total} materials' },
        'compound.prev_page': { zh: '上一页', en: 'Prev' },
        'compound.next_page': { zh: '下一页', en: 'Next' },
        'compound.mode_desc_only': { zh: '模式：仅显示当前组合', en: 'Mode: Current combination only' },
        'compound.mode_desc_combination': { zh: '模式：显示所有子组合（已存在组合）', en: 'Mode: All sub-combinations' },
        'compound.mode_desc_contains': { zh: '模式：显示包含所选元素的组合', en: 'Mode: Combinations containing selected elements' },
        'compound.article_theory': { zh: '理论', en: 'Theory' },
        'compound.article_experiment': { zh: '实验', en: 'Experiment' },
        'compound.review_status_approved': { zh: '已审核', en: 'Approved' },
        'compound.review_status_unreviewed': { zh: '未审核', en: 'Unreviewed' },
        'compound.review_status_rejected': { zh: '已拒绝', en: 'Rejected' },
        'compound.images_other': { zh: '其他截图', en: 'Other Images' },
        'compound.upload_doi': { zh: 'DOI', en: 'DOI' },
        'compound.upload_article_type': { zh: '文章类型', en: 'Article Type' },
        'compound.upload_sc_type': { zh: '超导体类型', en: 'SC Type' },
        'compound.crystal_structure_type': { zh: '晶体结构类型', en: 'Crystal Structure' },
        'compound.physical_data': { zh: '物理数据 (化学式/晶体结构/压强/Tc/λ等)', en: 'Physical Data (Formula/Structure/P/Tc/λ etc.)' },
        'compound.add_data_row': { zh: '+ 添加一组数据', en: '+ Add Data Row' },
        'compound.structure_file': { zh: '结构文件', en: 'Structure File' },
        'compound.pressure_gpa': { zh: '压强 (GPa)', en: 'Pressure (GPa)' },
        'compound.tc_k': { zh: 'Tc (K)', en: 'Tc (K)' },
        'compound.contributor_name': { zh: '贡献者姓名', en: 'Contributor Name' },
        'compound.contributor_affiliation': { zh: '贡献者单位', en: 'Affiliation' },
        'compound.images': { zh: '文献截图 (0-5张)', en: 'Screenshots (0-5)' },
        'compound.notes': { zh: '备注', en: 'Notes' },
        'compound.submit': { zh: '提交', en: 'Submit' },
        'compound.cancel': { zh: '取消', en: 'Cancel' },

        // ========== Login 登录页 ==========
        'login.title': { zh: '登录', en: 'Login' },
        'login.welcome': { zh: '欢迎登录', en: 'Welcome' },
        'login.admin_title': { zh: '管理员登录', en: 'Admin Login' },
        'login.user_title': { zh: '用户登录', en: 'User Login' },
        'login.subtitle': { zh: '使用同一账号即可访问用户和管理员功能', en: 'One account for both user and admin features' },
        'login.admin_subtitle': { zh: '通过管理员账号登录即可审核文献或管理其他管理员', en: 'Login as admin to review papers or manage other admins' },
        'login.user_subtitle': { zh: '使用邮箱和密码登录，访问上传与收藏功能', en: 'Log in with email and password to upload and manage papers' },
        'login.email': { zh: '邮箱', en: 'Email' },
        'login.password': { zh: '密码', en: 'Password' },
        'login.email_placeholder': { zh: 'you@example.com', en: 'you@example.com' },
        'login.password_placeholder': { zh: '请输入密码', en: 'Enter password' },
        'login.submit': { zh: '登录', en: 'Login' },
        'login.logging_in': { zh: '登录中...', en: 'Logging in...' },
        'login.no_account': { zh: '还没有账号？', en: 'No account?' },
        'login.no_admin_account': { zh: '还没有管理员账号？', en: 'No admin account?' },
        'login.register_now': { zh: '立即注册', en: 'Register Now' },
        'login.submit_application': { zh: '提交申请', en: 'Submit Application' },
        'login.session_exists': { zh: '已登录为 <strong>{name}</strong>。<a href="{url}" class="ms-2">立即前往</a> 或 <a href="#" onclick="window.authState.clear(); window.location.reload(); return false;">切换账号</a>', en: 'Logged in as <strong>{name}</strong>. <a href="{url}" class="ms-2">Go Now</a> or <a href="#" onclick="window.authState.clear(); window.location.reload(); return false;">Switch Account</a>' },

        // ========== Register 注册页 ==========
        'register.title': { zh: '注册', en: 'Register' },
        'register.admin_title': { zh: '申请成为管理员', en: 'Apply as Admin' },
        'register.user_title': { zh: '用户注册', en: 'User Registration' },
        'register.email': { zh: '邮箱', en: 'Email' },
        'register.email_hint': { zh: '将用于接收验证码和登录', en: 'Used for verification code and login' },
        'register.password': { zh: '密码', en: 'Password' },
        'register.password_confirm': { zh: '确认密码', en: 'Confirm Password' },
        'register.real_name': { zh: '真实姓名', en: 'Real Name' },
        'register.real_name_placeholder': { zh: '用于文献贡献者展示', en: 'Displayed as paper contributor' },
        'register.real_name_hint': { zh: '审核文献时将显示此姓名', en: 'This name will be displayed when reviewing papers' },
        'register.password_hint': { zh: '至少6位字符', en: 'At least 6 characters' },
        'register.send_code': { zh: '发送验证码', en: 'Send Verification Code' },
        'register.code_sent': { zh: '验证码已发送到您的邮箱，请在 5 分钟内完成验证', en: 'Verification code sent. Please verify within 5 minutes.' },
        'register.code_sent_to': { zh: '验证码已发送到 <strong>{email}</strong>，请查收。', en: 'Verification code sent to <strong>{email}</strong>.' },
        'register.verify_email': { zh: '验证邮箱', en: 'Verify Email' },
        'register.code_label': { zh: '验证码', en: 'Verification Code' },
        'register.code_placeholder': { zh: '6位数字', en: '6-digit code' },
        'register.code_input_label': { zh: '6位验证码', en: '6-Digit Code' },
        'register.complete_registration': { zh: '完成注册', en: 'Complete Registration' },
        'register.go_back': { zh: '返回重新填写', en: 'Go back' },
        'register.reenter_info': { zh: '重新填写信息', en: 'Re-enter Information' },
        'register.verify_success_title': { zh: '邮箱验证成功！', en: 'Email Verified!' },
        'register.verify_success_msg': { zh: '您的管理员申请已提交，请等待超级管理员审批。', en: 'Your admin application has been submitted. Please wait for super admin approval.' },
        'register.verify_success_notify': { zh: '审批通过后，您将收到邮件通知。', en: 'You will receive an email notification upon approval.' },
        'register.go_to_login': { zh: '前往登录页面', en: 'Go to Login' },
        'register.has_account': { zh: '已有账号？立即登录', en: 'Already have an account? Login' },
        'register.password_mismatch': { zh: '两次密码输入不一致！', en: 'Passwords do not match!' },
        'register.password_mismatch_short': { zh: '两次输入的密码不一致', en: 'Passwords do not match' },
        'register.success': { zh: '注册成功！', en: 'Registration successful!' },

        // ========== Admin 管理页 ==========
        'admin.dashboard': { zh: '管理面板', en: 'Admin Dashboard' },
        'admin.review_papers': { zh: '审核文献', en: 'Review Papers' },
        'admin.global_management': { zh: '全局管理', en: 'Global Management' },
        'admin.superadmin': { zh: '超级管理员', en: 'Super Admin' },
        'admin.pending_review': { zh: '待审核文献列表', en: 'Papers Pending Review' },
        'admin.no_pending': { zh: '目前没有待审核的文献', en: 'No papers pending review' },
        'admin.great_job': { zh: '太棒了！', en: 'Great Job!' },
        'admin.view_original': { zh: '查看原文', en: 'View Original' },
        'admin.detail_edit': { zh: '详情/编辑', en: 'Detail/Edit' },
        'admin.approve': { zh: '通过', en: 'Approve' },
        'admin.reject': { zh: '拒绝', en: 'Reject' },
        'admin.edit_paper': { zh: '编辑文献信息', en: 'Edit Paper' },
        'admin.save_changes': { zh: '保存修改', en: 'Save Changes' },
        'admin.doi_readonly': { zh: 'DOI (只读)', en: 'DOI (Read-only)' },
        'admin.title': { zh: '标题', en: 'Title' },
        'admin.journal': { zh: '期刊', en: 'Journal' },
        'admin.year': { zh: '年份', en: 'Year' },
        'admin.volume': { zh: '卷号', en: 'Volume' },
        'admin.authors': { zh: '作者', en: 'Authors' },
        'admin.authors_hint': { zh: 'JSON格式，如：["张三", "李四"]', en: 'JSON format, e.g.: ["Smith J", "Doe J"]' },
        'admin.article_type': { zh: '文章类型', en: 'Article Type' },
        'admin.superconductor_type': { zh: '超导体类型', en: 'SC Type' },
        'admin.review_status': { zh: '审核状态', en: 'Review Status' },
        'admin.compound_physical_data': { zh: '化合物与物理数据', en: 'Compound & Physical Data' },
        'admin.image_groups_intro': { zh: '图片分组与介绍', en: 'Image Groups & Intro' },
        'admin.contributor': { zh: '贡献者', en: 'Contributor' },
        'admin.contributor_affiliation': { zh: '贡献者单位', en: 'Affiliation' },
        'admin.notes': { zh: '备注', en: 'Notes' },
        'admin.add_data_row': { zh: '+ 添加一组数据', en: '+ Add Data Row' },
        'admin.at_least_one_data_row': { zh: '至少需要保留一组数据', en: 'At least one data row required' },
        'admin.paper_updated': { zh: '文献信息已更新！', en: 'Paper updated!' },
        'admin.loading_images': { zh: '正在加载图片分组...', en: 'Loading image groups...' },
        'admin.no_images': { zh: '暂无图片分组数据', en: 'No image group data' },
        'admin.group': { zh: '组', en: 'Group' },
        'admin.image': { zh: '图片', en: 'Image' },
        'admin.total_pending': { zh: '共 {total} 篇待审核文献', en: '{total} papers pending review' },
        'admin.all_users': { zh: '所有用户', en: 'All Users' },
        'admin.pending_approvals': { zh: '待审批管理员', en: 'Pending Approvals' },
        'admin.approved_admins': { zh: '已批准管理员', en: 'Approved Admins' },
        'admin.all_registered_users': { zh: '所有注册用户', en: 'All Registered Users' },
        'admin.refresh': { zh: '刷新列表', en: 'Refresh' },
        'admin.name': { zh: '姓名', en: 'Name' },
        'admin.email_col': { zh: '邮箱', en: 'Email' },
        'admin.reg_date': { zh: '注册日期', en: 'Registration Date' },
        'admin.permissions': { zh: '权限 (管理员)', en: 'Permissions (Admin)' },
        'admin.submitted': { zh: '提交文献', en: 'Papers Submitted' },
        'admin.reviewed': { zh: '审核文献', en: 'Papers Reviewed' },
        'admin.actions': { zh: '操作', en: 'Actions' },
        'admin.no_users': { zh: '暂无用户', en: 'No users' },
        'admin.superadmin_badge': { zh: '超级管理员', en: 'Super Admin' },
        'admin.admin_badge': { zh: '管理员', en: 'Admin' },
        'admin.regular_user': { zh: '普通用户', en: 'Regular User' },
        'admin.papers_count': { zh: '{count} 篇', en: '{count}' },
        'admin.verified': { zh: '已验证', en: 'Verified' },
        'admin.unverified': { zh: '未验证', en: 'Unverified' },
        'admin.no_pending_applications': { zh: '目前没有待审批的管理员申请', en: 'No pending admin applications' },
        'admin.total_admins': { zh: '共 {count} 位管理员', en: '{count} admins total' },
        'admin.approved_at': { zh: '批准时间', en: 'Approved At' },
        'admin.reviewed_papers_count': { zh: '审核文献数', en: 'Papers Reviewed' },
        'admin.approve_admin': { zh: '批准', en: 'Approve' },
        'admin.reject_admin': { zh: '拒绝', en: 'Reject' },
        'admin.click_view_papers': { zh: '点击查看文献', en: 'Click to view papers' },
        'admin.user_papers_title': { zh: '提交的文献列表', en: 'Submitted Papers' },
        'admin.no_papers_submitted': { zh: '该用户尚未提交任何文献。', en: 'This user has not submitted any papers.' },
        'admin.pending_status': { zh: '待审核', en: 'Pending' },
        'admin.manage_admins': { zh: '管理所有管理员', en: 'Manage Admins' },
        'admin.manage_all_papers': { zh: '管理全部文献', en: 'Manage All Papers' },
        'admin.paper_statistics': { zh: '平台文献统计', en: 'Paper Statistics' },
        'admin.not_verified': { zh: '❌ 未验证', en: '❌ Not Verified' },

        // ========== Tc Predict 预测页 ==========
        'tcpre.title': { zh: 'Tc 预测 (实验)', en: 'Tc Prediction (Lab)' },
        'tcpre.page_title': { zh: 'Tc 预测实验页', en: 'Tc Prediction Lab' },
        'tcpre.heading': { zh: 'Tc 预测（测试功能）', en: 'Tc Prediction (Beta)' },
        'tcpre.description': { zh: '上传一份 POSCAR 以及对应的 PDOS 数据（需包含 PDOS_H.dat），系统将在服务器上运行轻量版的 Tc 预测脚本，并返回估算结果。', en: 'Upload a POSCAR file and corresponding PDOS data (including PDOS_H.dat). The system will run a lightweight Tc prediction script and return estimated results.' },
        'tcpre.note_1': { zh: '目前仅支持 VASP 输出，PDOS 文件要求与原脚本一致', en: 'Currently only supports VASP output. PDOS file requirements same as original script.' },
        'tcpre.note_2': { zh: '至多读取 4 个金属 PDOS 文件，多余的将被忽略', en: 'At most 4 metal PDOS files are read; extras are ignored.' },
        'tcpre.note_3': { zh: '上传的文件只用于即时计算，不会被持久保存', en: 'Uploaded files are used for immediate calculation only and are not persisted.' },
        'tcpre.upload_contcar': { zh: 'POSCAR', en: 'POSCAR' },
        'tcpre.upload_pdos': { zh: 'PDOS 文件 (含 PDOS_H)', en: 'PDOS Files (incl. PDOS_H)' },
        'tcpre.pdos_hint': { zh: '选择 2~5 个 PDOS_*.dat 文件，其中必须包含 PDOS_H.dat。', en: 'Select 2-5 PDOS_*.dat files, must include PDOS_H.dat.' },
        'tcpre.predict': { zh: '开始预测', en: 'Start Prediction' },
        'tcpre.result': { zh: '预测结果', en: 'Prediction Result' },
        'tcpre.model_source': { zh: '模型来源 吉林大学物理学院 姜博文', en: 'Model by Jiang Bowen, School of Physics, Jilin University' },
        'tcpre.nav_element_table': { zh: '元素周期表', en: 'Periodic Table' },
    },

    /** 获取翻译文本 */
    t(key, params = {}) {
        const entry = this.dict[key];
        if (!entry) return key;
        let text = entry[this.lang] || entry['en'] || key;
        for (const [k, v] of Object.entries(params)) {
            text = text.replace(`{${k}}`, v);
        }
        return text;
    },

    /** 切换语言 */
    toggle() {
        this.lang = this.lang === 'zh' ? 'en' : 'zh';
        localStorage.setItem('lang', this.lang);
        this.applyToPage();
    },

    /** 设置语言 */
    set(lang) {
        this.lang = lang;
        localStorage.setItem('lang', lang);
        this.applyToPage();
    },

    /** 将翻译应用到当前页面 */
    applyToPage() {
        // 更新所有 data-i18n 元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const text = this.t(key);
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = text;
            } else {
                el.textContent = text;
            }
        });

        // 更新 data-i18n-placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });

        // 触发自定义事件让各页面 JS 响应语言切换
        document.dispatchEvent(new CustomEvent('langChange', { detail: { lang: this.lang } }));
    },

    /** 页面初始化时调用 */
    init() {
        this.applyToPage();
    }
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    I18N.init();
});
