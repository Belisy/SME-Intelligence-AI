import { redirect } from 'next/navigation'

/** 루트(/)는 /research로 바로 리다이렉트 */
export default function Home() {
  redirect('/research')
}
