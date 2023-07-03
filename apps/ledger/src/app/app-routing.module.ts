import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AccountListComponent } from './account-list/account-list.component';
import { TransactionListComponent } from './transaction-list/transaction-list.component';
import { PageNotFoundComponent } from './page-not-found/page-not-found.component';
import { AccountFormComponent } from './account-form/account-form.component';
import { TransactionFormComponent } from './transaction-form/transaction-form.component';

const routes: Routes = [
    { path: 'accounts', component: AccountListComponent },
    { path: 'accounts/:id/form', component: AccountFormComponent },
    { path: 'transactions', component: TransactionListComponent },
    { path: 'transactions/:id/form', component: TransactionFormComponent },
    { path: '', redirectTo: 'accounts', pathMatch: 'full' },
    { path: '**', component: PageNotFoundComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
