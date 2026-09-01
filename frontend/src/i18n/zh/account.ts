// 登录注册与账户中心文案。
// 认证错误码段（invalidCredentials 等）由 AuthContext 以机器键抛出，
// 消费组件用 t('account.' + message) 映射为界面文案，随语言切换。
export default {
  // ── 页面标题区 ──
  title: '用户中心',
  subtitle: '统一维护你的公开研究身份、账户安全和工作入口。',
  profileLoadFailed: '用户资料加载失败',

  // ── 头像与身份卡 ──
  emailVerified: '邮箱已验证',
  uploadAvatar: '上传头像',
  avatarUpdated: '头像已更新',
  avatarDeleted: '头像已删除',
  viewPublicProfile: '查看公开主页',

  // ── 个人资料 ──
  profileSection: '个人资料',
  profilePrivacyHint: '头像、用户名、真实姓名、所属机构、ORCID 和研究方向在填写后对所有访客公开；邮箱始终不公开。',
  realName: '真实姓名',
  realNameHelper: '可清空；每次变更都会留下审计记录',
  realNameConfirm: '真实姓名填写后会在公开主页展示，确认继续吗？',
  affiliation: '所属机构',
  researchInterests: '研究方向',
  interestsHelper: '使用逗号分隔，最多 10 项，每项最多 30 字',
  saveProfile: '保存资料',
  profileSaved: '个人资料已保存',

  // ── 设置正式用户名 ──
  setUsernameTitle: '设置正式用户名',
  usernameChangeWarning: '用户名只能由你修改一次；提交后旧公开主页地址立即失效。',
  confirmChange: '确认修改',
  usernameUpdated: '用户名已更新',

  // ── 我的论文 ──
  myPapers: '我的论文',
  myPapersHint: '你提交过的论文长期保存在这里，点击任意一条可只读复查提交内容。',

  // ── 账户安全 ──
  securitySection: '账户安全',
  securityHint: '修改成功后，其他设备和当前设备的旧登录状态都会失效。',
  currentPassword: '当前密码',
  newPassword: '新密码',
  passwordMinHint: '至少 10 位',
  passwordTooShort: '密码至少 10 位',
  changePassword: '修改密码',
  passwordChanged: '密码已修改，请重新登录',

  // ── 工作入口 ──
  workSection: '工作入口',
  enterAdmin: '进入管理员工作台',
  enterSuperAdmin: '进入超级管理员工作台',
  adminApplyHint: '管理员可参与科研内容审核。申请无需填写理由，但提交前必须完善真实姓名和所属机构。',
  applyAdmin: '申请成为管理员',
  adminApplied: '管理员申请已提交',
  rejectionReason: '原因：{reason}',
  withdraw: '撤回',
  applicationWithdrawn: '申请已撤回',
  applicationStatus: {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    withdrawn: '已撤回',
  },

  // ── 登录注册对话框 ──
  authTitle: '登录 / 注册',
  register: '注册',
  verifyEmailTitle: '验证邮箱',
  done: '完成',
  email: '邮箱',
  password: '密码',
  fillEmailPassword: '请填写邮箱和密码',
  fillRegisterFields: '请填写邮箱、密码和用户名',
  loginFailed: '登录失败',
  loginApprovalPending: '登录失败：您的管理员申请尚未通过审批',
  registerFailed: '注册失败',
  verifyFailed: '验证失败',
  resendFailed: '验证码发送失败',
  realNameOptional: '真实姓名（选填，填写后公开）',
  enterCode: '请输入验证码',
  codeSentBefore: '验证码已发送至',
  codeSentAfter: '，请查收邮件',
  codeLabel: '6 位验证码',
  verify: '验证',
  resendIn: '{seconds} 秒后可重新发送',
  resendCode: '重新发送验证码',
  switchToRegisterHint: '还没有账号？切换到「注册」标签',
  switchToLoginHint: '已有账号？切换到「登录」标签',

  // ── 公开主页 ──
  bannedNotice: '账号已封禁。历史贡献仍保留，但该账号当前不能登录或写入内容。',
  emptyPublicProfile: '该用户尚未完善公开研究资料。',

  // ── 认证错误码（AuthContext 抛出的机器键）──
  invalidCredentials: '邮箱或密码错误',
  emailNotVerified: '邮箱未验证，请先完成邮箱验证',
  approvalPending: '您的管理员申请尚未通过审批，请耐心等待',
  emailRegistered: '该邮箱已注册',
  emailTaken: '该邮箱已占用其他用户名',
  usernameTaken: '用户名已被占用',
  emailOrUsernameTaken: '邮箱或用户名已被占用',
  sendCodeFailed: '发送验证码失败，请稍后重试',
  userNotFound: '用户不存在，请先注册',
  alreadyVerified: '邮箱已验证，请直接登录',
  invalidCode: '验证码错误',
  codeExpired: '验证码已过期，请重新获取',
  sessionExpired: '登录状态已失效',
  usernameUpdateFailed: '用户名修改失败',
  networkError: '网络异常，请稍后重试',
} as const
