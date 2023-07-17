import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, flatMap } from 'rxjs';
import { Account } from './models/account';
import { Tag } from './models/tag';
import { TagPrimitive } from './types/tagPrimitive';
import { Transaction } from './models/transaction';
import { TransactionPrimitive }  from './types/transactionPrimitive';
import { AccountPrimitive }  from './types/accountPrimitive';
import { TransactionList } from './types/transactionList';

@Injectable({
  providedIn: 'root'
})
export class LedgerService {

    constructor(
        private http: HttpClient
    ) {}

    getAccounts(): Observable<Account[]> {
        return this.http.get<AccountPrimitive[]>('/ledger/accounts').pipe(
            map(primitives => primitives.map(primitive => new Account(primitive)))
        );
    }

    getTags(): Observable<Tag[]> {
        return this.http.get<TagPrimitive[]>('/ledger/tags').pipe(
            map(primitives => primitives.map(primitive => new Tag(primitive)))
        );
    }

    getTransactions(query: string, limit: number, offset: number, account: number, tag: string): Observable<TransactionList> {
         let params = {
             limit,
             offset,
             account,
             tag: tag || '',
             q: query || '',
         };

        return this.http.get<TransactionList>('/ledger/transactions', {params,});
    }

    getAccount(uid: number): Observable<Account> {
        return this.http.get<AccountPrimitive>(`/ledger/accounts/${uid}`).pipe(
            map((primitive) => new Account(primitive))
        );
    }

    getTransaction(uid: number): Observable<Transaction> {
        return this.http.get<TransactionPrimitive>(`/ledger/transactions/${uid}`).pipe(
            map((primitive) => new Transaction(primitive))
        );
    }

    addAccount(primitive: AccountPrimitive): Observable<Account> {
        return this.http.post<Account>('/ledger/accounts', primitive)
    }

    addTransaction(primitive: TransactionPrimitive): Observable<Transaction> {
        return this.http.post<Transaction>('/ledger/transactions', primitive);
    }

    updateAccount(primitive: AccountPrimitive): Observable<void> {
        const url = `/ledger/accounts/${primitive.uid}`;
        return this.http.put<void>(url, primitive);
    }

    updateTransaction(primitive: TransactionPrimitive): Observable<void> {
        const url = `/ledger/transactions/${primitive.uid}`;
        return this.http.put<void>(url, primitive);
    }

    deleteAccount(uid: number): Observable<void> {
        return this.http.delete<void>(`/ledger/accounts/${uid}`);
    }

    deleteTransaction(uid: number): Observable<void> {
        return this.http.delete<void>(`/ledger/transactions/${uid}`);
    }

    autocompletePayee(payee: string): Observable<TransactionList> {
        return this.http.get<TransactionList>(
            `/ledger/transactions?q=payee:${payee}&limit=1`
        );
    }
}
