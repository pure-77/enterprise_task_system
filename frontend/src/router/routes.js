import MainLayout from '@/layouts/MainLayout.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: MainLayout,
    meta: { requiresAuth: true, requiresWorkspace: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard/Index.vue')
      },
      {
        path: 'tasks',
        name: 'TaskList',
        component: () => import('@/views/Task/List.vue')
      },
      {
        path: 'tasks/:id',
        name: 'TaskDetail',
        component: () => import('@/views/Task/Detail.vue')
      },
      {
        path: 'tasks/edit/:id',
        name: 'TaskEdit',
        component: () => import('@/views/Task/Edit.vue')
      },
      {
        path: 'categories',
        name: 'CategoryList',
        component: () => import('@/views/Category/Index.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/Statistics/Index.vue')
      },
      {
        path: 'profile',
        name: 'UserProfile',
        component: () => import('@/views/User/Profile.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'tags',
        name: 'Tags',
        component: () => import('@/views/User/Tags.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'backup',
        name: 'Backup',
        component: () => import('@/views/User/Backup.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'workspaces',
        name: 'WorkspaceList',
        component: () => import('@/views/Workspace/List.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'workspaces/create',
        name: 'WorkspaceCreate',
        component: () => import('@/views/Workspace/Create.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'workspaces/:id/settings',
        name: 'WorkspaceSettings',
        component: () => import('@/views/Workspace/Settings.vue'),
        meta: { requiresWorkspace: false }
      },
      {
        path: 'invitations',
        name: 'Invitations',
        component: () => import('@/views/Invitation/Index.vue')
      },
      // ===== 新模块路由 =====
      {
        path: 'agent',
        name: 'Agent',
        component: () => import('@/views/agent/Index.vue'),
        meta: { title: '智能助手' }
      },
      {
        path: 'im',
        name: 'IM',
        component: () => import('@/views/im/Index.vue'),
        meta: { title: '即时通讯' }
      },
      {
        path: 'approval',
        name: 'Approval',
        component: () => import('@/views/approval/Index.vue'),
        meta: { title: 'OA审批' }
      },
      {
        path: 'approval/:id',
        name: 'ApprovalDetail',
        component: () => import('@/views/approval/Detail.vue'),
        meta: { title: '审批详情' }
      },
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('@/views/calendar/Index.vue'),
        meta: { title: '日程日历' }
      },
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('@/views/attendance/Index.vue'),
        meta: { title: '考勤打卡' }
      },
      {
        path: 'announcements',
        name: 'Announcements',
        component: () => import('@/views/announcement/Index.vue'),
        meta: { title: '企业公告' }
      },
      {
        path: 'announcements/:id',
        name: 'AnnouncementDetail',
        component: () => import('@/views/announcement/Detail.vue'),
        meta: { title: '公告详情' }
      },
      {
        path: 'files',
        name: 'Files',
        component: () => import('@/views/file/Index.vue'),
        meta: { title: '文件管理' }
      },
      {
        path: 'org/departments',
        name: 'OrgDepartments',
        component: () => import('@/views/org/DeptManage.vue'),
        meta: { title: '部门管理' }
      },
      {
        path: 'org/members',
        name: 'OrgMembers',
        component: () => import('@/views/org/MemberRoster.vue'),
        meta: { title: '成员花名册' }
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/notification/Index.vue'),
        meta: { title: '通知中心' }
      },
    ]
  },
  {
    path: '/auth',
    name: 'Auth',
    component: BlankLayout,
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/views/Auth/Login.vue')
      },
      {
        path: 'register',
        name: 'Register',
        component: () => import('@/views/Auth/Register.vue')
      },
      {
        path: 'forgot-password',
        name: 'ForgotPassword',
        component: () => import('@/views/Auth/ForgotPassword.vue')
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
]

export default routes
