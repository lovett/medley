import { AccountPrimitive } from './accountPrimitive';

export type TransactionPrimitive = {
    uid: number;
    account_id?: number;
    account?: AccountPrimitive;
    payee: string;
    amount: number;
    occurred_on: string;
    cleared_on?: string;
    note?: string;
}
