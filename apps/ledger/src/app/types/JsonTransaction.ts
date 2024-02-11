import { JsonAccount } from './JsonAccount';
import { JsonTag } from './JsonTag';

export type JsonTransaction = {
    uid: number;
    account: JsonAccount;
    destination?: JsonAccount;
    payee: string;
    amount: number;
    occurred_on: string;
    cleared_on?: string;
    note?: string;
    tags: string[];
    receipt_name?: string;
    receipt?: File;
}
