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
      // 结算单更新
      {
        path: 'settlement/actual',
        name: 'SettlementActual',
        component: () => import('@/views/settlement/ActualSettlement.vue'),
        meta: { title: '结算单更新 / 实际结算单更新' },
      },
      {
        path: 'settlement/jiaojiang',
        name: 'SettlementJiaojiang',
        component: () => import('@/views/settlement/JiaojiangSim.vue'),
        meta: { title: '结算单更新 / 椒江模拟结算单更新' },
      },
      {
        path: 'settlement/general',
        name: 'SettlementGeneral',
        component: () => import('@/views/settlement/generalSim.vue'),
        meta: { title: '结算单更新 / 通用模拟结算单更新' },
      },

      {
        path: 'monthly-extract',
        name: 'MonthlyExtract',
        component: () => import('@/views/monthly-report/PdfExtract.vue'),
        meta: { title: '结算单 PDF 数据提取' },
      },


      {
        path: 'node-edit',
        name: 'NodeEdit',
        component: () => import('@/views/node-edit/index.vue'),
        meta: { title: '节点编辑' },
      },
      {
        path: 'settings/contract-config',
        name: 'ContractConfig',
        component: () => import('@/views/settings/ContractConfig.vue'),
        meta: { title: '设置 / 中长期合约配置' },
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
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || ''
  document.title = title ? `${title} - 电力工具助手` : '电力工具助手'
})

export default router