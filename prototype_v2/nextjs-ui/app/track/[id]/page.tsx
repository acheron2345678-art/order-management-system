import OrderTracker from "../../../components/OrderTracker";
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;return <OrderTracker orderId={Number(id)}/>;}
