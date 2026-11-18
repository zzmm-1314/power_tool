import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import BasicLayout from '@/layouts/BasicLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: BasicLayout,
    redirect: '/load-analysis',
    children: [
      // 负荷分析
      {
        path: 'load-analysis',
        name: 'LoadAnalysis',
        component: () => import('@/views/load-analysis/index.vue'),
        meta: { title: '负荷分析' },
      },

      // 日前电价
      {
        path: 'day-ahead-price/unified',
        name: 'DayAheadUnified',
        component: () => import('@/views/day-ahead-price/UnifiedSettlement.vue'),
        meta: { title: '日前电价 / 统一结算点' },
      },
      {
        path: 'day-ahead-price/plant',
        name: 'DayAheadPlant',
        component: () => import('@/views/day-ahead-price/PlantNode.vue'),
        meta: { title: '日前电价 / 电厂节点' },
      },

      // 价差分析
      {
        path: 'price-spread/unified',
        name: 'SpreadUnified',
        component: () => import('@/views/price-spread/UnifiedSettlement.vue'),
        meta: { title: '价差分析 / 统一结算点' },
      },
      {
        path: 'price-spread/plant',
        name: 'SpreadPlant',
        component: () => import('@/views/price-spread/PlantNode.vue'),
        meta: { title: '价差分析 / 电厂节点' },
      },
      // 中长期合约
      {
        path: 'contract/decomposition',
        name: 'ContractDecomposition',
        component: () => import('@/views/contract/ContractDecomposition.vue'),
        meta: { title: '中长期合约 / 合约分解' },
      },
      {
        path: 'contract/position',
        name: 'ContractPosition',
        component: () => import('@/views/contract/ContractPosition.vue'),
        meta: { title: '中长期合约 / 电厂合约仓位' },
      },
      {
        path: 'contract/rolling-profit',
        name: 'RollingProfit',
        component: () => import('@/views/contract/RollingProfit.vue'),
        meta: { title: '中长期合约 / 滚撮收益模拟' },
      },
      {
        path: 'contract/cross-province-profit',
        name: 'CrossProvinceProfit',
        component: () => import('@/views/contract/CrossProvinceProfit.vue'),
        meta: { title: '中长期合约 / 长三角省间交易收益模拟' },
      },
      {
        path: 'settlement/price-compare',
        name: 'PriceCompare',
        component: () => import('@/views/settlement/PriceCompare.vue'),
        meta: { title: '电价对比' },
      },
      // 结算单更新
      {
        path: 'settlement/actual',
        name: 'SettlementActual',
        component: () => import('@/views/settlement/ActualSettlement.vue'),
        meta: { title: '结算单更新 / 实际结算单更新' },
      },
      {
        path: 'settlement/simulate',
        name: 'SettlementSimulate',
        component: () => import('@/views/settlement/SimulationSim.vue'),
        meta: { title: '结算单更新 / 模拟结算单' },
      },
      {
        path: 'monthly-report',
        name: 'MonthlyReport',
        component: () => import('@/views/monthly-report/index.vue'),
        meta: { title: '月报数据部分填充' },
      },
      {
        path: 'monthly-extract',
        name: 'MonthlyExtract',
        component: () => import('@/views/monthly-report/PdfExtract.vue'),
        meta: { title: '结算单 PDF 数据提取' },
      },
      // 工具助手
      {
        path: 'tools/doc-compare',
        name: 'DocCompare',
        component: () => import('@/views/tools/DocCompare.vue'),
        meta: { title: '工具助手 / 文档逐字比对' },
      },
      {
        path: 'contract/config', // 原来是 settings/contract-config
        name: 'ContractConfig',
        component: () => import('@/views/settings/ContractConfig.vue'), // 可以移动文件位置
        meta: { title: '中长期合约 / 合约配置' },
      },
      {
        path: 'unified-plants',
        name: 'UnifiedPlants',
        component: () => import('@/views/unified-plants/index.vue'),
        meta: { title: '统调电厂' },
      },
      {
        path: 'coefficient',
        name: 'Coefficient',
        component: () => import('@/views/coefficient/index.vue'),
        meta: { title: '申报系数预测' },
      },
      {
        path: 'rolling',
        name: 'Rolling',
        component: () => import('@/views/rolling/index.vue'),
        meta: { title: '滚撮分析' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/load-analysis',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || ''
  document.title = title ? `${title} - 电力工具助手` : '电力工具助手'
})

export default router