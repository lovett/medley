import { AccountPrimitive } from './accountPrimitive';

export type TransactionPrimitive = {
    uid: number;
    account_id?: number;
    destination_id?: number;
    account?: AccountPrimitive;
    destination?: AccountPrimitive;
    payee: string;
    amount: number;
    occurred_on: string;
    cleared_on?: string;
    note?: string;
    tags: string[];
    receipt_name?: string;
    receipt?: File;
}
