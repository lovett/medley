import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { Account } from './models/account';
import { Transaction } from './models/transaction';
import { TransactionList } from './models/transactionList';

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

    getTransactions(): Observable<TransactionList> {
        return this.http.get<TransactionList>('/ledger/transactions');
    }

    getAccount(uid: number): Observable<Account> {
        return this.http.get<Account>(`/ledger/accounts/${uid}`);
    }

    getTransaction(uid: number): Observable<Transaction> {
        return this.http.get<Transaction>(`/ledger/transactions/${uid}`);
    }

    addAccount(account: Account): Observable<Account> {
        console.log(account);
        return this.http.post<Account>('/ledger/accounts', account, {
            headers: new HttpHeaders({
                'Content-Type': 'application/json'
            }),
        })
    }

    addTransaction(transaction: Transaction): Observable<Transaction> {
        console.log(transaction);
        return this.http.post<Transaction>('/ledger/transactions', transaction, {
            headers: new HttpHeaders({
                'Content-Type': 'application/json'
            }),
        });
    }

    updateAccount(account: Account): Observable<void> {
        const headers = new HttpHeaders({
            'Content-Type': 'application/json',
        });

        const url = `/ledger/accounts/${account.uid}`;

        console.log(url);

        return this.http.put<void>(url, account, {headers,});
    }

    updateTransaction(transaction: Transaction): Observable<void> {
        const headers = new HttpHeaders({
            'Content-Type': 'application/json'
        });

        const url = `/ledger/transactions/${transaction.uid}`;
        console.log(url);

        return this.http.put<void>(url, transaction, {headers,});

    }

    deleteAccount(uid: number): Observable<void> {
        return this.http.delete<void>(`/ledger/accounts/${uid}`);
    }

    deleteTransaction(uid: number): Observable<void> {
        return this.http.delete<void>(`/ledger/transactions/${uid}`);
    }

    autocompletePayee(payee: string): Observable<TransactionList> {
        return this.http.get<TransactionList>(
            `/ledger/transactions?q=payee:${payee}&limit=1`,
            {
                headers: new HttpHeaders({
                    'Content-Type': 'application/json'
                }),
            })
    }
}
