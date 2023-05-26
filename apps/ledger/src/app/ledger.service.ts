import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { Account } from './models/account';
import { Transaction } from './models/transaction';
import { TransactionPrimitive }  from './types/transactionPrimitive';
import { TransactionList } from './types/transactionList';

@Injectable({
  providedIn: 'root'
})
export class LedgerService {

    constructor(
        private http: HttpClient
    ) {}

    getAccounts(): Observable<Account[]> {
        return this.http.get<Account[]>('/ledger/accounts');
    }

    getTransactions(query?: string): Observable<TransactionList> {
        let params = {};
        if (query) {
            params = {q: query};
        }

        return this.http.get<TransactionList>('/ledger/transactions', {params,});
    }

    getAccount(uid: number): Observable<Account> {
        return this.http.get<Account>(`/ledger/accounts/${uid}`);
    }

    getTransaction(uid: number): Observable<Transaction> {
        return this.http.get<TransactionPrimitive>(`/ledger/transactions/${uid}`).pipe(
            map((primitive) => new Transaction(primitive))
        );
    }

    addAccount(account: Account): Observable<Account> {
        console.log(account);
        return this.http.post<Account>('/ledger/accounts', account)
    }

    addTransaction(primitive: TransactionPrimitive): Observable<Transaction> {
        return this.http.post<Transaction>('/ledger/transactions', primitive);
    }

    updateAccount(account: Account): Observable<void> {
        const url = `/ledger/accounts/${account.uid}`;
        return this.http.put<void>(url, account);
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
